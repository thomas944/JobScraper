# Table of Contents
- [Usage](#usage)
- [Installation](#installation)
  - [venv Setup](#venv-setup)
  - [Debugger Setup](#debugger-setup)
- [In Progress](#in-progress)


# Usage
> This tool helps simplify the tedious task of searching and reading through job descriptions by quickly scraping the availble jobs and filtering by **location, years of experience, degree**

> *THIS TOOL DOES NOT COMPLETELY AUTOMATE EVERYTHING AND IS STILL A WORK IN PROGRESS. IT JUST HELPS FILTER REDUCE THE AMOUNT OF TIME READING JOB DESCRIPTIONS*. 

> It is only compatible with companies that user Workday as of now, and the user still needs to manually add the link to company's Workday site as well as manually apply.

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

3. `companies.csv` contains all the companies. If your desired company is not present in the `companies.csv`, feel free to add it and make a pull request. The link is the company's Workday link. You should try your best to add as many filters as possible to reduce the search space, and after that paste the link inside the spreadsheet

4. Create a folder called `testing/`

5. Upon completion, the program will create a `{company-name}.csv` for each company containing the valid jobs that fit the criteria inside the `testing/` folder

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


### In Progress
- Different modes, mode 1: scrape everything in links.csv, mode 2: scrape only specific target companies, or industries
- Create a UI
- Create a file for jobs posted today
- Create a file for jobs expiring soon
- Allow user to filter by industry, company name, etc
- Support other job portals besides Workday