from selenium.common.exceptions import UnexpectedAlertPresentException, NoSuchElementException
from selenium import webdriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import pyautogui

import json
import time

cancel_for_testing = False

def find_user_email(email):
    # check if in email list already - Transfer To
    select = driver.find_element_by_name("components:certapaySendTransfer:Recipient:componentMarkup:select")
    for option in select.find_elements_by_tag_name('option'):
        if email in option.text:
            option.click()
            return True
    return False

# def confirm_receipt(prev_windows_count):
#     receipt = driver.find_element_by_css_selector("a[title='Print Receipt']")
#     receipt.click()
#
#     time.sleep(2)
#
#     WebDriverWait(driver, 1800).until(
#         EC.number_of_windows_to_be(prev_windows_count)
#     )
#
#     x = driver.execute_script("""
#         const confirmPromise = new Promise((resolve, reject) => {
#             result = confirm('Click OK when you are ready to continue');
#             resolve(result);
#         });
#         confirmPromise.then((result) => {
#             console.log(result);
#             return result;
#         }).catch(rejection => {
#             console.log("REJECTED!");
#         });
#     """)
#     time.sleep(2)
#     WebDriverWait(driver, 1800).until(
#         not EC.alert_is_present()
#     )
#     print(x)
#     return x


if __name__ == "__main__":
    with open("member_data.json", "r") as f:
        member_data = json.load(f)

    with open("transfer_data.json", "r") as f:
        transfer_data = json.load(f)

    emails = []
    with open("emails.txt", "r") as f:
        for email in f.readlines():
            emails.append(email.strip())
    # remove any duplicates
    emails = list(set(emails))

    # chrome_options = Options()
    # disable popup print dialog so we can use Robot to save PDF
    # chrome_options.add_argument("--disable-print-preview")
    # driver = webdriver.Chrome(options=chrome_options)

    driver = webdriver.Chrome()

    # begin
    driver.get("https://online.islandsavings.ca/OnlineBanking/")
    el = driver.find_element_by_id("branch")
    for option in el.find_elements_by_tag_name('option'):
        if option.text == member_data['branch']:
            option.click()

    el = driver.find_element_by_id("acctnum")
    el.clear()
    el.send_keys(member_data['member_number'])

    el = driver.find_element_by_id("pac")
    el.clear()
    el.send_keys(member_data['password'])

    el = driver.find_element_by_id("Continue")
    el.click()

    # check if logon triggered security question
    try:
        el = driver.find_element_by_class_name("mdIALogonChallenge")

        if "security_questions" in member_data:
            el = driver.find_element_by_css_selector("label[for='answer']")
            security_q = el.text
            security_input = driver.find_element_by_id("answer")
            for q_and_a in member_data['security_questions'].values():
                if (q_and_a['q'] in security_q):
                    security_input.send_keys(q_and_a['a'])
                    el = driver.find_element_by_id("Continue")
                    el.click()

    except Exception as e:
        print(e)

    # wait for up to 30 minutes for user to enter security question
    transfers = WebDriverWait(driver,1800).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "a[title='Transfers']"))
    )
    transfers.click()

    etransfer = driver.find_element_by_css_selector("a[href='/OnlineBanking/Transfers/EmailMoney/'")
    etransfer.click()

    for email in emails:
        # # check if in email list already - Transfer To
        # select = driver.find_element_by_id("id1")
        # for option in select.find_elements_by_tag_name('option'):
        #     if email in option.text:
        #         option.click()
        #         break

        if not find_user_email(email):
            new = driver.find_element_by_css_selector("a[title='Add a new recipient'")
            new.click()

            # figure out if it's an email or a phone number
            is_email = True if '@' in email else False
            if is_email:
                name = email[:email.find('@')]

                # id's are changing each page load
                email_phone_input = driver.find_element_by_name("components:RecipientEditPanel:Email:componentMarkup:textfield")
            else:
                name = email

                email_phone_input = driver.find_element_by_name("components:RecipientEditPanel:MobilePhone:componentMarkup:textfield")

            email_phone_input.send_keys(email)
            name_input = driver.find_element_by_name("components:RecipientEditPanel:Name:componentMarkup:textfield")
            name_input.send_keys(name)

            select = driver.find_element_by_name("components:RecipientEditPanel:NotificationIndicator:componentMarkup:select")
            choice = "Email" if is_email else "Mobile phone"
            for option in select.find_elements_by_tag_name('option'):
                if choice in option.text:
                    option.click()
                    break

            question = driver.find_element_by_name("components:RecipientEditPanel:securityPanel:SecurityQ:componentMarkup:textfield")
            question.send_keys(transfer_data['security_question'])
            answer = driver.find_element_by_name("components:RecipientEditPanel:securityPanel:Answer:componentMarkup:textfield")
            answer.send_keys(transfer_data['security_answer'])

            add = driver.find_element_by_css_selector("input[title='Add Recipient']")
            add.click()

            confirm = driver.find_element_by_css_selector("input[title='Confirm']")
            confirm.click()

            # select the new user
            find_user_email(email)

        # check if they have autotransfer enabled
        try:
            autotransfer_checkbox = driver.find_element_by_class_name("acknowledgeCheckbox")
            autotransfer_checkbox.click()
        except NoSuchElementException:
            pass

        # Transfer from
        select = driver.find_element_by_name("components:certapaySendTransfer:fromAcct:componentMarkup:select")
        for i, option in enumerate(select.find_elements_by_tag_name('option')):
            if i == 1:
                option.click()
                break

        # now send the transfer!
        amount = driver.find_element_by_name("components:certapaySendTransfer:Amount:Amount:componentMarkup:textfield")
        amount.send_keys(transfer_data['amount'])
        message_box = driver.find_element_by_name("components:certapaySendTransfer:Message:componentMarkup:textarea")
        message_box.send_keys(transfer_data['message'])
        send_transfer = driver.find_element_by_name("buttonPanel:actions:continue")
        send_transfer.click()

        if not cancel_for_testing:
            confirm = driver.find_element_by_css_selector("input[title='Confirm']")
            confirm.click()

            prev_windows_count = len(driver.window_handles)

            receipt = driver.find_element_by_css_selector("a[title='Print Receipt']")
            receipt.click()

            time.sleep(2)

            WebDriverWait(driver, 1800).until(
                EC.number_of_windows_to_be(prev_windows_count)
            )

            # while not confirm_receipt(prev_windows_count):
            #     continue
            # receipt = driver.find_element_by_css_selector("a[title='Print Receipt']")
            # receipt.click()
            #
            # time.sleep(2)
            #
            # WebDriverWait(driver, 1800).until(
            #     EC.number_of_windows_to_be(prev_windows_count)
            # )
            #
            # return_val = driver.execute_script("""
            #     return (confirm('Click OK when you are ready to continue'))
            # """)
            # if return_val == "false":
            #
            #
            # time.sleep(1)

            # difficulties automating print window
            # print_window = driver.window_handles[-1]
            # driver.switch_to.window(print_window)
            # print_preview_app = driver.find_element_by_xpath("//print-preview-app")
            # print_preview_app = driver.find_element_by_xpath("//print-preview-app")
            # content = WebElement(driver.execute_script("return arguments[0].shadowRoot", print_preview_app))
            # preview_header = content.find_element_by_css_selector("print-preview-header")
            # header_content = WebElement(driver.execute_script("return arguments[0].shadowRoot", preview_header))
            # save = header_content.find_element_by_class_name("action-button")
            # save.click()

        else:
            cancel = driver.find_element_by_css_selector("a[title='Cancel'")
            cancel.click()


        # wait for up to 30 minutes for user to save PDF and click on e-transfer again
        etransfer_page = WebDriverWait(driver, 1800).until(
            EC.presence_of_element_located((By.NAME, "components:certapaySendTransfer:Recipient:componentMarkup:select"))
        )
        # try:
        #     # wait for user to confirm PDF save
        #     driver.execute_script("alert('Click OK when you are ready to continue');")
        # except UnexpectedAlertPresentException:
        #     print("error")
        #
        # time.sleep(30)
        # etransfer.click()

        # chrome://print is outside the scope of selenium
        # save_receipt = driver.find_element_by_class_name("action-button")
        # save_receipt.click()

        # time.sleep(5)
        # pyautogui.press('enter')

        # automating GUI is a bit trickier - rely on user input for now









