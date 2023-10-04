import queue
from selenium import webdriver
from time import sleep
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.firefox.options import Options

class Unsubscriber:

    max_wait = 5;
    
    def login_to_inbox (self):
        self.browser.get ("https://login.yahoo.com")
        self.browser.find_element (By.ID, "login-username").send_keys ("email") #replace with your email
        self.browser.find_element (By.ID, "login-signin").click();
        self.browser.find_element (By.ID, "login-passwd").send_keys ("password") #replace with your password
        self.browser.find_element (By.ID, "login-signin").click();
        self.browser.find_element (By.ID, "ybarMailLink").click();


    def click_if_exists (self, by, code, parent):
        try:
            element = parent.find_element (by, code)
            self.browser.execute_script ("arguments[0].scrollIntoView(true);", element)
            element.click()
            return True
        except Exception:
            return False

    def unsubscribe (self):
        emailbody = self.browser.find_element (By.XPATH, "//div[@data-test-id='message-body-container']")

        #click any possible link
        self.browser.implicitly_wait (0)
        link_keywords = ["Unsubscribe", "Let", "Opt out", "Remove", "Update", "Preference", "Message", "Subscription"]
        word_index = 0
        success = False
        while not success and word_index < len(link_keywords):
            success = self.click_if_exists (By.XPATH, f".//a[contains(text(),'{link_keywords[word_index]}')]", emailbody) or \
                self.click_if_exists (By.XPATH, f".//a[contains(text(), '{link_keywords[word_index].lower()}')]", emailbody)
            word_index = word_index + 1
        
        if not success:
            success = self.click_if_exists (By.XPATH, ".//*[contains(text(),'Remove me from future messages')]", self.browser)

        if not success:
            raise Exception ("No link found")
 
        #switch to new tab
        self.browser.switch_to.window(self.browser.window_handles[2]);
        self.browser.implicitly_wait (10)
        try:
            self.browser.find_element (By.TAG_NAME, "div")
        except NoSuchElementException:
            pass
        sleep (3)
        self.browser.implicitly_wait (0)

        #click all checkboxes
        checkboxes = self.browser.find_elements (By.XPATH, "//input[@type='checkbox']")
        for box in checkboxes:
            try:
                self.browser.execute_script ("arguments[0].scrollIntoView(true);", box)
                box.click()
            except Exception:
                continue

        sleep (1)

        #click any possible buttons
        success = False
        with open ("button_xpaths.txt", "r") as button_file:
            xpaths = [xpath.strip() for xpath in button_file.readlines()]
            path_index = 0
            while not success and path_index < len(xpaths):
                success = self.click_if_exists (By.XPATH, xpaths[path_index], self.browser)
                path_index = path_index + 1

        if not success:
            success = self.click_if_exists (By.ID, "unsuball", self.browser) or self.click_if_exists (By.TAG_NAME, "button", self.browser) 

        if not success:
            raise Exception ("No button found")

        sleep (1)
        self.browser.implicitly_wait (self.max_wait)
        self.browser.close()
        self.browser.switch_to.window(self.browser.window_handles[1])

        return success

    def is_college_email (self, email):

        sender = email.find_element (By.XPATH, ".//span[@class='o_h J_x em_N G_e']")
        sender_name = sender.text.lower()
        sender_email = sender.get_attribute ("title")
        body = email.text.lower()

        if sender_email[-4:] != ".edu" and sender_email[-4:] != ".org":
            return False
        if sender_email[-4:] == ".edu":
            return True
        if "university" in sender_name or "college" in sender_name or "admissions" in sender_name:
            return True
        if "application" in body or "apply" in body or "applied" in body:
            return True

        return False

    def close_tabs (self):
        while len(self.browser.window_handles) > 1:
            self.browser.switch_to.window (self.browser.window_handles[-1])
            self.browser.close()
        self.browser.switch_to.window (self.browser.window_handles[0])
        sleep(1)
        self.browser.implicitly_wait (5)

    def in_lists (self, check_domain, whitelist, blacklist):
        return any(domain.strip() in check_domain for domain in whitelist) or any(domain.strip() in check_domain for domain in blacklist)

    def refresh_emails (self, visited):
        email_list = self.browser.find_element (By.XPATH, "//ul[@class='M_0 P_0 ']")
        emails = email_list.find_elements (By.TAG_NAME, "a")
        #print ("refresh: " + str(len(emails)))
        return [email for email in emails if email not in visited]

    # unsubscribe from and delete college emails
    # adds the domain to the blacklist so won't be visited again
    def unsubscribe_all (self, depth):
        with webdriver.Firefox() as browser:
            self.browser = browser
            browser.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            browser.implicitly_wait(self.max_wait)

            self.login_to_inbox ()

            with open ("whitelist.txt", "r") as whitelist_file:
                whitelist = set(whitelist_file.readlines())
            blacklist_file = open ("blacklist.txt", "r+")
            blacklist = set(blacklist_file.readlines())

            emails_visisted = []

            emails_scanned = 0
            while emails_scanned < depth:
                emails = self.refresh_emails (emails_visisted)

                while len(emails) > 0:     
                    email = emails.pop (0) #get next email         
                    emails_visisted.append (email) #update emails visited
                    emails_scanned = emails_scanned + 1
                    if emails_scanned > 30:
                        emails_visisted.pop (0)

                    browser.execute_script ("arguments[0].scrollIntoView(true);", email)

                    #ignore ads
                    try:
                        email_address = email.find_element (By.XPATH, ".//span[@class='o_h J_x em_N G_e']").get_attribute ("title")
                    except Exception:
                        continue

                    #check if email is from a college and not in whitelist / blacklist
                    if self.is_college_email (email) and not self.in_lists (email_address, whitelist, blacklist):
                        #open email in new tab
                        link = email.get_attribute('href')
                        browser.execute_script(f"window.open('{link}', '_blank');");
                        sleep (2)
                        self.browser.switch_to.window(self.browser.window_handles[1]);

                        blacklist.add (email_address.split("@")[1])

                        try:
                            #unsubscribe
                            self.unsubscribe()
                            print ("unsubscribed from " + email_address)
                            sleep (1)
                            browser.find_element (By.XPATH, "//button[@data-test-id='toolbar-delete']").click()
                            sleep (1)
                            blacklist_file.write (email_address.split("@")[1] + "\n")
                        except Exception as e:
                            print ("failed to unsubscribe from " +  email_address + " " + str(e));

                        self.close_tabs()
                        sleep (1)
                        emails = self.refresh_emails (emails_visisted)

            blacklist_file.close()

    # delete all college emails without unsubscribing, regardless of if they are in the blacklist
    # you can call this after unsubscribing to delete any repeat emails from the same domain
    def delete (self, depth):
        deleted = 0
        histo = {}

        options = Options()
        options.headless = True

        with webdriver.Firefox(options=options) as browser:
            print ("starting deletion")

            self.browser = browser
            actions = ActionChains (browser)
            browser.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            browser.implicitly_wait(self.max_wait)

            self.login_to_inbox ()

            with open ("whitelist.txt", "r") as whitelist_file:
                whitelist = set(whitelist_file.readlines())

            emails = []
            emails_visisted = []
            emails_scanned = 0

            while emails_scanned < depth:
                attempts = 0
                while attempts < 4 and len(emails) == 0:
                    sleep (1)
                    emails = self.refresh_emails (emails_visisted)
                    attempts = attempts + 1

                if len(emails) == 0:
                    break

                while len(emails) > 0:     
                    email = emails.pop (0) #get next email         
                    emails_visisted.append (email) #update emails visited
                    emails_scanned = emails_scanned + 1
                    if emails_scanned > 200:
                        emails_visisted.pop (0)

                    #ignore ads
                    try:
                        browser.execute_script ("arguments[0].scrollIntoView(true);", email)
                        email_address = email.find_element (By.XPATH, ".//span[@class='o_h J_x em_N G_e']").get_attribute ("title")
                        email_domain = email_address.split("@")[1]
                    except Exception:
                        continue

                    #check if email is from a college and not in whitelist / blacklist
                    if self.is_college_email (email) and not self.in_lists (email_address, whitelist, []):
                        actions.move_to_element (email).perform()
                        trash = email.find_element (By.XPATH, ".//div[@class='p_R D_F ek_EZ ab_C H_6D6F']")
                        actions.move_to_element (trash).click().perform()

                        deleted = deleted + 1
                        if email_domain in histo:
                            histo[email_domain] = histo[email_domain] + 1
                        else:
                            histo[email_domain] = 1

                        print (f"email from {email_address} deleted")

                        sleep (0.1)

                print ("----------------")
                most_emails_from = ""
                for item in histo.items():
                    if most_emails_from not in histo or item[1] > histo[most_emails_from]:
                        most_emails_from = item[0]
                    print (f"{item[0]} : {item[1]}")

                print (f"{emails_scanned} emails scanned, {deleted} emails deleted")
                if deleted > 0:
                    print (f"Most emails from: {most_emails_from} - {histo[most_emails_from]}")
                print ("----------------")


unsub = Unsubscriber ()
unsub.unsubscribe_all (5630)

