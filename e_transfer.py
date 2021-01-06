# from selenium.common.exceptions import (
#     UnexpectedAlertPresentException,
#     NoSuchElementException,
#     TimeoutException,
# )
# from selenium.webdriver.remote.webelement import WebElement
# from selenium.webdriver.chrome.options import Options

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException

import json
import time
from collections import OrderedDict


# given a select from driver query, iterate over options until desired option is found
def _select_option(select, target):
    for option in select.find_elements_by_tag_name("option"):
        if target in option.text:
            option.click()
            return True
    return False


def clean_cell(number, raw=False):
    # accept different formats of phone number
    number = number.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    # turn it into Island Savings desired format
    if not raw:
        number = f"({number[:3]}) {number[3:6]}-{number[6:]}"

    return number


# name is user-provided in case of name already present error
def try_add_recipient(transfer_data, contact, is_email, name=None):
    print(f"{contact} not present in select list - adding...")
    new = driver.find_element_by_css_selector("a[title='Add a new recipient']")
    new.click()

    if not name:
        name = (
            contact[: contact.find("@")]
            if "@" in contact
            else clean_cell(contact, raw=True)
        )
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
    choice = "Email" if is_email else "Mobile phone"
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

        driver.get(
            "https://online.islandsavings.ca/OnlineBanking/Transfers/EmailMoney/"
        )
    except NoSuchElementException:
        confirm = driver.find_element_by_css_selector("input[title='Confirm']")
        confirm.click()

        # Check for any errors - again, program continues normally when there is an exception.
        try:
            # raises NoSuchElementException
            errors = driver.find_element_by_class_name("errors")
            error_message = errors.find_element_by_tag_name("p").text
            if "431" in error_message:
                name = (
                    contact[: contact.find("@")]
                    if "@" in contact
                    else clean_cell(contact, raw=True)
                )
                print(
                    f"{name} already exists as a name in the list. Skipping {contact}"
                )
            else:
                print(f"Error occured. Skipping {contact}.")
                print(f"Error message: {error_message}")

            driver.get(
                "https://online.islandsavings.ca/OnlineBanking/Transfers/EmailMoney/"
            )

        except NoSuchElementException:
            return


def add_new_contacts(transfer_data, contacts):
    for contact in contacts:
        # figure out if it's an email or a phone number
        is_email = True if "@" in contact else False

        # If it's a phone number, make sure it's in Island Savings format.
        if not is_email:
            contact = clean_cell(contact)

        try:
            # Raises NoSuchElementException.
            if not _select_option(
                driver.find_element_by_name(
                    "components:certapaySendTransfer:Recipient:componentMarkup:select"
                ),
                contact,
            ):
                try_add_recipient(transfer_data, contact, is_email)
            else:
                print(f"{contact} already present in select list")

        except NoSuchElementException:
            # If there are currently no contacts, then the recipient select will not be present.
            try_add_recipient(transfer_data, contact, is_email)


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
    driver.get("https://online.islandsavings.ca/OnlineBanking/")
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
    # select the new user
    _select_option(
        driver.find_element_by_name(
            "components:certapaySendTransfer:Recipient:componentMarkup:select"
        ),
        contact,
    )

    # check if they have autotransfer enabled
    try:
        # wait up to 2 seconds for autotransfer box to appear
        autotransfer_span = WebDriverWait(driver, 2).until(
            EC.presence_of_element_located((By.CLASS_NAME, "acknowledgeText"))
        )
        autotransfer_span.click()

        # autotransfer_checkbox = driver.find_element_by_class_name("acknowledgeCheckbox")
        # # on linux clicking on span does not work sometimes
        # if not autotransfer_checkbox.is_selected():
        #     autotransfer_checkbox.click()
    except (NoSuchElementException, TimeoutException):
        pass

    # Transfer from
    select = driver.find_element_by_name(
        "components:certapaySendTransfer:fromAcct:componentMarkup:select"
    )
    # Assuming that the account transferring from is chequing acct (or first option).
    # TODO: check that this is a list and don't iterate use try/except
    for i, option in enumerate(select.find_elements_by_tag_name("option")):
        if i == 1:
            option.click()
            break

    # now send the transfer!
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

        time.sleep(2)

        WebDriverWait(driver, 1800).until(
            EC.number_of_windows_to_be(prev_windows_count)
        )

    else:
        # Cancel, just go to transfer page.
        driver.get(
            "https://online.islandsavings.ca/OnlineBanking/Transfers/EmailMoney/"
        )

    # TODO
    # wait for up to 30 minutes for user to save PDF and click on e-transfer again
    # etransfer_page = WebDriverWait(driver, 1800).until(
    #     EC.presence_of_element_located(
    #         (
    #             By.NAME,
    #             "components:certapaySendTransfer:Recipient:componentMarkup:select",
    #         )
    #     )
    # )


def send_transfers(transfer_data, contacts):
    for contact in contacts:
        try_send_transfer(transfer_data, contact)


def main():
    with open("member_data.json", "r") as f:
        member_data = json.load(f)

    with open("transfer_data.json", "r") as f:
        transfer_data = json.load(f)

    contacts = []
    with open("contacts2.txt", "r") as f:
        # ignore blank lines
        contacts = [line.strip() for line in f.readlines() if line.strip()]
    # remove any duplicates
    contacts = list(OrderedDict.fromkeys(contacts))

    login(member_data)
    try_answer_security_questions(member_data)

    # Once we're in we can just use the URL directly.
    driver.get("https://online.islandsavings.ca/OnlineBanking/Transfers/EmailMoney/")

    add_new_contacts(transfer_data, contacts)
    send_transfers(transfer_data, contacts)


if __name__ == "__main__":

    CANCEL_FOR_TESTING = True
    # Set driver as a global variable since all functions will use it.
    driver = webdriver.Chrome()

    main()
