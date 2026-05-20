# Table of Contents
- [Usage](#usage)
- [Installation](#installation)
  - [venv Setup](#venv-setup)
  - [Debugger Setup](#debugger-setup)



# Usage
1. Set up your virtual environment for dependencies (optional, but recommended). Navigate to `#venv-setup` for instructions

> venv is the recommended virtual environment

2. Find the `settings.json` file, and adjust the values to fit your needs

|Property|Type|Description|
|---|---|---|
|`MIN_YOE`| `int` | Min range of experience |
|`MAX_YOE`| `int` | Max range of experience |
|`BLOCKED_TITLE_WORDS`| `[]str` | Job Title keywords to filter out in lowercase |
|`BLOCKED_COUNTRIES`| `[]str` | Countries to filter out in lowercase |
|`DEGREES`| `[]str` | All your degrees. **Must be of type "PhD","Master's", "Bachelor's"** |

3. `companies.csv` contains all the companies. If your company is not there, feel free to add it and make a pull request. The link is the company's Workday link. You should try your best to add as many filters as possible, and after that paste the link inside the spreadsheet.

# Installation
## venv Setup
1. Create a virtual environment with the command. Optionally replace `.venv` with your desired name. 
```
python -m venv .venv
```

2. Activate your virtual environment. Your command line path should update with the name of your virtual environment
```
.\.venv\Scripts\activate
```

3. Install the packages
```
pip install -r requirements.txt
```

4. Verify installation
```
pip list
```

## Debugger Setup
Optional steps to set up debugger (recommended if developer)
1. Create a folder called `.vscode` if you don't already have

2. Create a `settings.json` file with this content
```json
{
    "python.terminal.activateEnvironment": true
}
```

3. Create a `launch.json` file with this content. Locate your python installation, copy the absolute path, and use it for the `"python":` field. The path should be similar to this `~/.venv/scripts/python.exe`
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python Debugger: Module",
            "type": "debugpy",
            "request": "launch",
            "module": "main",
            "args": [],
            "python": #TODO: Path to python folder
        }
    ]
}
```

4. Close and reopen your IDE

5. Set a breakpoint and press `Run` -> `Start Debugging`. You should jump to your breakpoint


## Setting up 
TODO: Different modes, mode 1: scrape everything in links.csv, mode 2: scrape only specific target companies, or industries