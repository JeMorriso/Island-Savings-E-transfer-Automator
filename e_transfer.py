from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException

import json
from collections import OrderedDict
import argparse
import time


# given a select from driver query, iterate over options until desired option is found
def _select_option(select, target):
    """Iterate over select elements until target is found.

    Select the target option in the browser if found.

    Return:
        bool: Whether or not the target was found.
    """
    for option in select.find_elements_by_tag_name("option"):
        if target in option.text:
            option.click()
            return True
    return False


def is_email(contact):
    # figure out if it's an email or a phone number
    return True if "@" in contact else False


def sanitize_contact(contact, raw=False):
    """
    Args:
        raw (bool): Whether or not to 'prettify' the phone number. The reason for this
            parameter is that if adding a name, the form doesn't allow parentheses or
            hyphen.
    """
    # If it's a phone number, make sure it's in Island Savings format.
    if not is_email(contact):
        # accept different formats of phone number
        contact = (
            contact.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        )
        # turn it into Island Savings desired format
        if not raw:
            contact = f"({contact[:3]}) {contact[3:6]}-{contact[6:]}"

    return contact


def generate_contact_name(contact):
    return (
        contact[: contact.find("@")]
        if is_email(contact)
        else sanitize_contact(contact, raw=True)
    )


def try_add_recipient(transfer_data, contact):

    if driver.current_url != E_TRANSFER_URL:
        driver.get(E_TRANSFER_URL)

    print(f"{contact} not present in select list - adding...")
    new = driver.find_element_by_css_selector("a[title='Add a new recipient']")
    new.click()

    name = generate_contact_name(contact)
    contact_input = (
        driver.find_element_by_name(
            "components:RecipientEditPanel:Email:componentMarkup:textfield"
        )
        if "@" in contact
        else driver.find_element_by_name(
            "components:RecipientEditPanel:MobilePhone:componentMarkup:textfield"
        )
    )
    contact_input.send_keys(contact)
    name_input = driver.find_element_by_name(
        "components:RecipientEditPanel:Name:componentMarkup:textfield"
    )
    name_input.send_keys(name)

    select = driver.find_element_by_name(
        "components:RecipientEditPanel:NotificationIndicator:componentMarkup:select"
    )
    choice = "Email" if is_email(contact) else "Mobile phone"
    _select_option(select, choice)

    question = driver.find_element_by_name(
        "components:RecipientEditPanel:securityPanel:SecurityQ:componentMarkup:textfield"
    )
    question.send_keys(transfer_data["security_question"])
    answer = driver.find_element_by_name(
        "components:RecipientEditPanel:securityPanel:Answer:componentMarkup:textfield"
    )
    answer.send_keys(transfer_data["security_answer"])

    add = driver.find_element_by_css_selector("input[title='Add Recipient']")
    add.click()

    # Check for bad input error - if there is no error, an exception is raised, and the program continues normally.
    try:
        # Raises NoSuchElementException.
        errors = driver.find_element_by_class_name("errors")
        error_list = errors.find_element_by_tag_name("ol")
        print(f"{contact} cannot be added! Errors discovered:")
        for error in error_list.find_elements_by_tag_name("li"):
            print(error.find_element_by_tag_name("span").text)

        if driver.current_url != E_TRANSFER_URL:
            driver.get(E_TRANSFER_URL)

    except NoSuchElementException:
        confirm = driver.find_element_by_css_selector("input[title='Confirm']")
        confirm.click()

        # Check for any errors - again, program continues normally when there is an exception.
        try:
            # raises NoSuchElementException
            errors = driver.find_element_by_class_name("errors")
            error_message = errors.find_element_by_tag_name("p").text
            if "431" in error_message:
                name = generate_contact_name(contact)
                print(
                    f"{name} already exists as a name in the list. Skipping {contact}"
                )
            else:
                print(f"Error occured. Skipping {contact}.")
                print(f"Error message: {error_message}")

            if driver.current_url != E_TRANSFER_URL:
                driver.get(E_TRANSFER_URL)

        except NoSuchElementException:
            return


def add_contacts(transfer_data, contacts):
    if contacts is None:
        print("No contacts list provided. Exiting.")

    if driver.current_url != E_TRANSFER_URL:
        driver.get(E_TRANSFER_URL)

    for contact in contacts:
        contact = sanitize_contact(contact)

        try:
            # Raises NoSuchElementException.
            if not _select_option(
                driver.find_element_by_name(
                    "components:certapaySendTransfer:Recipient:componentMarkup:select"
                ),
                contact,
            ):
                try_add_recipient(transfer_data, contact)
            else:
                print(f"{contact} already present in select list")

        except NoSuchElementException:
            # If there are currently no contacts, then the recipient select will not be
            # present.
            try_add_recipient(transfer_data, contact)


def delete_contacts(contacts=None):
    """
    For this function I am not able to create a dict of contacts to buttons, because
    deleting a contact requires a page change, so the buttons change every time I go
    back to the contacts page

    Instead I can walk through the contact rows, deleting necessary rows, and keeping
    track of where I left off.
    """

    def _gen_rows():
        """Create list of table rows corresponding to recipients after loading page."""
        driver.get(CONTACTS_URL)
        # get summary group
        contact_table = driver.find_element_by_class_name("summarygroup")
        odd_rows = contact_table.find_elements_by_class_name("odd")
        even_rows = contact_table.find_elements_by_class_name("even")
        num_rows = len(odd_rows) + len(even_rows)

        zipped_rows = list(zip(odd_rows, even_rows))
        table_rows = []

        for o, e in zipped_rows:
            table_rows.append(o)
            table_rows.append(e)
        # Append last row if odd number of rows
        if num_rows % 2 == 1:
            table_rows.append(odd_rows[-1])
        return table_rows

    sanitized_contacts = None
    if contacts is not None:
        sanitized_contacts = set([sanitize_contact(c) for c in contacts])

    index = 0
    bad_deletes = 0
    table_rows = _gen_rows()
    while True:
        try:
            # Both elements should be lists of length 2.
            # Raises IndexError.
            row = table_rows[index]
            contact = row.find_elements_by_class_name("name")[1].text
            if contacts is None or contact in sanitized_contacts:
                print(f"{contact} present in select list - deleting...")
                # Raises IndexError.
                delete_btn = row.find_elements_by_css_selector("div.control > a")[0]
                delete_btn.click()

                confirm = driver.find_element_by_css_selector("input[value='Confirm']")
                confirm.click()

                # Check for delete error - if there is no error, an exception is raised,
                # and the program continues normally.
                try:
                    # Raises NoSuchElementException.
                    errors = driver.find_element_by_class_name("errors")
                    # The first paragraph holds the error message.
                    error_msg = errors.find_element_by_tag_name("p")
                    print(f"{contact} cannot be deleted! Errors discovered:")
                    print(error_msg.text)
                    index += 1
                    bad_deletes += 1
                except NoSuchElementException:
                    pass

                table_rows = _gen_rows()
            else:
                # Skipped a contact, so ignore all skipped contacts by incrementing
                # index. Contacts stored in alpha order so guaranteed to work.
                index += 1

        # After the list is iterated, get index error that functions as terminate
        # condition for while loop.
        except IndexError:
            if len(table_rows) > 0 and contacts is None or bad_deletes > 0:
                print("Some contacts were not able to be deleted. Exiting.")
            else:
                print("All desired contacts have been successfully deleted. Exiting.")
            return


def try_answer_security_questions(member_data):
    # check if logon triggered security question
    try:
        el = driver.find_element_by_class_name("mdIALogonChallenge")

        if "security_questions" in member_data:
            el = driver.find_element_by_css_selector("label[for='answer']")
            security_q = el.text
            security_input = driver.find_element_by_id("answer")
            for q_and_a in member_data["security_questions"].values():
                if q_and_a["q"] in security_q:
                    security_input.send_keys(q_and_a["a"])
                    el = driver.find_element_by_id("Continue")
                    el.click()

    except NoSuchElementException:
        print("Bypassed security questions...")

    try:
        # Wait up to 30 minutes for security questions to be answered
        WebDriverWait(driver, 1800).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a[title='Transfers']"))
        )
    except TimeoutException:
        print("Timed out waiting for security questions to be answered.")


def login(member_data):
    driver.get(HOME_URL)
    el = driver.find_element_by_id("branch")
    for option in el.find_elements_by_tag_name("option"):
        if option.text == member_data["branch"]:
            option.click()

    el = driver.find_element_by_id("acctnum")
    el.clear()
    el.send_keys(member_data["member_number"])

    el = driver.find_element_by_id("pac")
    el.clear()
    el.send_keys(member_data["password"])

    el = driver.find_element_by_id("Continue")
    el.click()


def try_send_transfer(transfer_data, contact):
    if driver.current_url != E_TRANSFER_URL:
        driver.get(E_TRANSFER_URL)

    # select the new user
    if not _select_option(
        driver.find_element_by_name(
            "components:certapaySendTransfer:Recipient:componentMarkup:select"
        ),
        contact,
    ):
        print(f"Contact {contact} not found in select list. Skipping {contact}...")
        return

    # check if they have autotransfer enabled
    try:
        # Having problems in this section
        time.sleep(2)
        # wait up to 2 seconds for autotransfer box to appear
        autotransfer_div = WebDriverWait(driver, 2).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.acknowledgeCheckbox"))
        )

        autotransfer_div.click()
        # Check that the checkbox is actually clicked - need to access the input element
        # itself - checking the div will not work.
        if not driver.find_element_by_css_selector(
            "input.acknowledgeCheckbox"
        ).is_selected():
            print(f"Autotransfer checkbox could not be clicked. Skipping {contact}...")

    except (NoSuchElementException, TimeoutException):
        pass

    # Transfer from
    select = driver.find_element_by_name(
        "components:certapaySendTransfer:fromAcct:componentMarkup:select"
    )
    # Raises IndexError.
    select.find_elements_by_tag_name("option")[1].click()
    amount = driver.find_element_by_name(
        "components:certapaySendTransfer:Amount:Amount:componentMarkup:textfield"
    )
    amount.send_keys(transfer_data["amount"])
    message_box = driver.find_element_by_name(
        "components:certapaySendTransfer:Message:componentMarkup:textarea"
    )
    message_box.send_keys(transfer_data["message"])
    send_transfer = driver.find_element_by_name("buttonPanel:actions:continue")
    send_transfer.click()

    if not CANCEL_FOR_TESTING:
        confirm = driver.find_element_by_css_selector("input[title='Confirm']")
        confirm.click()

        prev_windows_count = len(driver.window_handles)

        receipt = driver.find_element_by_css_selector("a[title='Print Receipt']")
        receipt.click()

        # Wait for user to handle print window.
        # I don't think this is strictly necessary, because it seems like the driver is
        # suspended while the print window is open, but it shouldn't hurt to keep it.
        WebDriverWait(driver, 1800).until(
            EC.number_of_windows_to_be(prev_windows_count)
        )


def send_transfers(transfer_data, contacts):
    if contacts is None:
        print("No contacts list provided. Exiting.")

    try:
        for contact in contacts:
            try_send_transfer(transfer_data, contact)
    except IndexError:
        print(
            "Bank account used to send e-transfers was not found (1st option in the list). Something is wrong."
        )


def add_contacts_and_send_transfers(transfer_data, contacts):
    """DEPRECATED"""
    add_contacts(transfer_data, contacts)
    send_transfers(transfer_data, contacts)


def process_contact_list(fname):
    # Empty strings are falsy.
    if not fname:
        return None

    try:
        with open(fname, "r") as f:
            # ignore blank lines
            contacts = [line.strip() for line in f.readlines() if line.strip()]
    except FileNotFoundError:
        print(f"{fname} not found. Exiting.")
        exit(1)

    return list(OrderedDict.fromkeys(contacts))


def main():
    try:
        with open("member_data.json", "r") as f:
            member_data = json.load(f)
    except FileNotFoundError:
        print("member_data.json not found. Exiting.")
        exit(1)

    try:
        with open("transfer_data.json", "r") as f:
            transfer_data = json.load(f)
    except FileNotFoundError:
        if (
            args.add
            or all(el is False for el in [args.add, args.send, args.delete])
            or args.send
        ):
            print("""transfer_data.json not found. Exiting.""")
            exit(1)
    try:
        with open("file_names.json", "r") as f:
            file_names = json.load(f)
    except FileNotFoundError:
        if (
            args.add
            or all(el is False for el in [args.add, args.send, args.delete])
            or args.send
        ):
            print("""file_names.json not found. Exiting""")
            exit(1)

    login(member_data)
    try_answer_security_questions(member_data)

    try:
        # Add is default behaviour
        if args.add or all(el is False for el in [args.add, args.send, args.delete]):
            contacts = process_contact_list(file_names["add_file"])
            add_contacts(transfer_data, contacts)
        if args.send:
            contacts = process_contact_list(file_names["send_file"])
            send_transfers(transfer_data, contacts)
        if args.delete:
            contacts = process_contact_list(file_names["delete_file"])
            delete_contacts(contacts)
    except KeyError:
        print("file_names.json is incorrectly formed. Exiting.")
        exit(1)


if __name__ == "__main__":

    CANCEL_FOR_TESTING = True
    HOME_URL = "https://online.islandsavings.ca/OnlineBanking/"
    E_TRANSFER_URL = (
        "https://online.islandsavings.ca/OnlineBanking/Transfers/EmailMoney/"
    )
    CONTACTS_URL = (
        "https://online.islandsavings.ca/OnlineBanking/Transfers/ManageContacts/"
    )
    # Set driver as a global variable since all functions will use it.
    driver = webdriver.Chrome()

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--add",
        action="store_true",
        help="Add contacts in list. If no argument is provided, this is the default behaviour.",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Delete contacts in list. If no list is provided, delete all contacts.",
    )
    parser.add_argument(
        "--send",
        action="store_true",
        help="Send e-transfers to all contacts in list.",
    )

    args = parser.parse_args()

    main()
