# DualCanvas

DualCanvas is a local desktop prototype for editing two linked RGBA canvases (A and B) through a pixel permutation map.
Painting on one canvas automatically updates the corresponding mapped pixels on the other canvas.

## What This Repo Contains

- `visual_anagram_editor/main.py`: PyQt6 desktop application entry point.
- `visual_anagram_editor/controller.py`: core brush/erase/undo/redo + permutation propagation logic.
- `visual_anagram_editor/permutation_model.py`: permutation loading and coordinate mapping.
- `visual_anagram_editor/canvas_widget.py`: Qt canvas widget and zoom/paint behavior.

## Requirements

- Python 3.10+ (3.11 or 3.12 recommended)
- pip (bundled with Python)
- OS: Windows 11, macOS, or Linux (instructions below focus on Windows 11)

Python packages used:

- `numpy`
- `Pillow`
- `PyQt6`

## Windows 11 Setup (Python Not Installed Yet)

### 1. Install Python on Windows 11

1. Go to: `https://www.python.org/downloads/windows/`
2. Download the latest stable Python 3 installer for Windows (`64-bit`).
3. Run installer:
   - Check `Add Python to PATH` on the first screen.
   - Click `Install Now`.
4. Open **PowerShell** and verify:

```powershell
py --version
```

If this prints a Python version (for example `Python 3.12.x`), installation succeeded.

### 2. Get the Project Locally

If you already have the repository, skip this step. Otherwise:

```powershell
git clone git@github.com:JulianAdamek/dualcanvas.git
cd dualcanvas
```

If SSH is not configured, you can clone with HTTPS instead:

```powershell
git clone https://github.com/JulianAdamek/dualcanvas.git
cd dualcanvas
```

### 3. Create and Activate a Virtual Environment (Optional, Recommended)

From the repository root:

```powershell
py -3 -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks script execution, run this once in the same terminal:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Then activate again:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 4. Install Dependencies

With the virtual environment active:

```powershell
python -m pip install --upgrade pip
pip install numpy Pillow PyQt6
```

## Launching the App

From the repository root, with virtual environment active:

```powershell
python -m visual_anagram_editor.main
```

You should see a window titled `Visual Anagram Editor (Prototype)`.

## How to Use the Editor

1. Load permutation:
   - `File` -> `Load permutation...`
   - Choose a `.npy` file containing a 1D bijective permutation of `0..N-1`.
   - `N` must be a perfect square (the app infers a square image `sqrt(N) x sqrt(N)`).
2. Optionally load a starting image:
   - `File` -> `Load image into A...` or `Load image into B...`
   - The image is converted to RGBA and resized to the permutation dimensions.
3. Paint with toolbar tools:
   - `Brush`, `Eraser`, `Eyedropper`
   - Brush `Size`
   - Brush `Opacity` (0-100%)
   - Color picker button
4. Toggle piece outlines:
   - Toolbar `Piece Outlines` or `View` -> `Show Piece Outlines`
5. Undo/redo:
   - `Ctrl+Z` / `Ctrl+Y`
6. Save outputs:
   - `File` -> `Save canvas A...`
   - `File` -> `Save canvas B...`

## Notes on Permutation Files

Expected format for permutation `.npy`:

- NumPy array, shape `(H*W,)`, integer values.
- Contains each index exactly once (bijective).
- Minimum index `0`, maximum index `H*W - 1`.
- `H*W` must be a perfect square.

If these constraints are not met, the app raises validation errors while loading.

## Troubleshooting (Windows)

- `py` command not found:
  - Reinstall Python and ensure `Add Python to PATH` is checked.
- `ModuleNotFoundError` for `PyQt6` / `numpy` / `PIL`:
  - Make sure virtual environment is activated, then reinstall packages.
- App does not start from file path execution:
  - Run as module from repo root:
    - `python -m visual_anagram_editor.main`
  - This is required because the package uses relative imports.

## License

This repository is licensed under the MIT License. See `LICENSE`.
