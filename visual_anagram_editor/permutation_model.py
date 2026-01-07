import numpy as np
from dataclasses import dataclass


@dataclass
class PermutationModel:
    H: int
    W: int
    perm: np.ndarray  # shape (H*W,), dtype=int64
    inv_perm: np.ndarray  # shape (H*W,), dtype=int64

    @classmethod
    def from_npy(cls, path: str) -> "PermutationModel":
        perm_raw = np.load(path)
        if perm_raw.ndim != 1:
            raise ValueError("Permutation must be a 1D array")

        N = perm_raw.size
        if np.unique(perm_raw).size != N:
            raise ValueError("Permutation is not bijective")
        if perm_raw.min() != 0 or perm_raw.max() != N - 1:
            raise ValueError("Permutation indices must be 0..N-1")

        side = int(np.sqrt(N))
        if side * side != N:
            raise ValueError("Permutation size must form a square image")

        inv_perm = np.empty_like(perm_raw)
        inv_perm[perm_raw] = np.arange(N, dtype=perm_raw.dtype)

        return cls(H=side, W=side, perm=perm_raw.astype(np.int64), inv_perm=inv_perm.astype(np.int64))

    def forward_map_index(self, idxA: int) -> int:
        return int(self.perm[idxA])

    def inverse_map_index(self, idxB: int) -> int:
        return int(self.inv_perm[idxB])

    def map_coords_A_to_B(self, y: int, x: int) -> tuple[int, int]:
        idxA = y * self.W + x
        idxB = self.perm[idxA]
        yB, xB = divmod(int(idxB), self.W)
        return yB, xB

    def map_coords_B_to_A(self, y: int, x: int) -> tuple[int, int]:
        idxB = y * self.W + x
        idxA = self.inv_perm[idxB]
        yA, xA = divmod(int(idxA), self.W)
        return yA, xA
