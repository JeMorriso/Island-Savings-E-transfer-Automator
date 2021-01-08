# Island Savings E-transfer Automator

> A Python script that uses Selenium for handling bulk e-transfers for the Island Savings credit union. Bulk addition of recipients, deletion of recipients, and sending of e-transfers is supported.

## Installation (on Mac)

1. Do one of the following:

   - Clone the repository by entering `git clone https://github.com/JeMorriso/Island-Savings-E-transfer-Automator.git` in your command prompt / terminal.
   - Download the zip file (click the 'Code' button on the Github page for this repository), unzip it, and store it somewhere you will remember.

2. Download the matching ChromeDriver version to the Chrome version installed on your PC here: (https://chromedriver.chromium.org/downloads) - the zip file is called chromedriver_mac64.zip
   2b. Unzip the file and put the executable in the folder "usr/local/bin"

3. The Mac should have Python installed on it. So you need to go to the "terminal" application and type in "pip install selenium" and your installation is finished.

## Usage

There are three ways to use this program. See below for descriptions of the supporting files.

### Add recipients

`python e_transfer.py --add`

This is the default function, so `--add` may be omitted.

`add_file` in `file_names.json` must point to the text file that the contacts to be added are stored in.

### Send transfers

`python e_transfer.py --send`

This function first adds all the recipients in the associated text file, and then sends them all an e-transfer using the information found in `transfer_data.json`. This function requires user input after the transfer step in order to save or print the receipt. After this is done (or cancelled) the program will automatically resume execution.

### Delete recipients

`python e_transfer.py --delete`

Delete all the recipients in the associated text file pointed to in `file_names.json`. If there is no file name is entered, delete all contacts.

---

There are three `.json` files that can be filled in in depending on which operations you want to perform. The file structure for each can be found in the examples below, or in the sample files included with this repository.

### member_data.json

This file automates the login process. 'security questions' is an optional key. If you add it, the program will attempt to answer the security question that appears. **This file stores sensitive information so keep it in a safe place**.

```json
{
  "branch": "Your Island Savings branch, as found in the dropdown menu when you login",
  "member_number": "Your member number",
  "password": "Your password",
  "security_questions": {
    "q1": { "q": "One of your security questions", "a": "Its answer" },
    "q2": { "q": "q2", "a": "a2" },
    "q3": { "q": "q3", "a": "a3" }
  }
}
```

### transfer_data.json

This file is necessary if you plan on adding recipients or sending transfers.

```json
{
  "security_question": "Security question that the recipient must answer",
  "security_answer": "The answer to the question",
  "amount": "Amount (in dollars) of the transfer",
  "message": "Optional message for the recipient"
}
```

### file_names.json

This file is used for storing the names of the text files that are associated with the add, send and delete functions. The files should have the extension `.txt`. You only need to fill in files for the functions you want to perform. If you are deleting contacts, you can leave the value empty (like `""`) in which case the entire contacts list will be deleted.

```json
{
  "add_file": "contacts-to-add.txt",
  "send_file": "contacts-to-send-transfers-to.txt",
  "delete_file": "contacts-to-delete.txt"
}
```

---

### Recipient .txt file structures

The text files for storing contacts for addition, deletion, or sending transfers should have the following format:

```txt
fake@email.com
2501234567
250-123-4567
(250) 123 4567
```

If an email is used, the part before `@` will be used as the recipient's name. If a phone number is used, the unformatted number will be used (`2501234567` in the example above).
