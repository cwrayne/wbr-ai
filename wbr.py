import logging
import re
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoAlertPresentException, TimeoutException, NoSuchElementException

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

API_KEY = "DEEPINFRA_KEY"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}"
}
BASE_URL = "https://api.deepinfra.com/v1/openai"


def query_ai(prompt, context=None):
    system_message = (
        "You are an AI designed to play an abstract version of Rock Paper Scissors. "
        "Respond with a creative, single word or very short phrase that beats the given word in a playful sense. "
        "Do not use punctuation, capitalization, or typical rock-paper-scissors elements. "
        "Keep the response concise."
    )
    if context:
        system_message += f" Remember: {context}"

    payload = {
        "model": "meta-llama/Meta-Llama-3.1-405B-Instruct",
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ]
    }

    try:
        response = requests.post(f"{BASE_URL}/chat/completions", json=payload, headers=HEADERS)
        response.raise_for_status()  # Raise an error on a failed request
        data = response.json()
        answer = data['choices'][0]['message']['content'].strip()
        return answer
    except requests.exceptions.RequestException as e:
        logging.error(f"Error querying AI: {e}")
        return None

def setup_webdriver():
    options = Options()
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920x1080')
    driver = webdriver.Chrome(options=options)
    return driver

def handle_alert(driver):
    try:
        alert = WebDriverWait(driver, 2).until(EC.alert_is_present())
        if alert:
            alert = driver.switch_to.alert
            logging.info(f"Alert text: {alert.text}")
            alert.accept()
            return True
    except (TimeoutException, NoAlertPresentException):
        logging.info("No alert was present.")
    return False

def play_game():
    driver = setup_webdriver()
    driver.get("https://www.whatbeatsrock.com")

    try:
        while True:
            successful_beats = 0  # Reset counter for each new game session
            wait = WebDriverWait(driver, 15)

            while True:
                if handle_alert(driver):
                    continue

                try:
                    word_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "p.text-2xl.text-center")))
                    word_html = word_element.get_attribute("outerHTML")
                    logging.info(f"Raw Element HTML: {word_html}")

                    match = re.search(r'^<p.*?>([^<]+)', word_html)
                    if not match:
                        logging.error("No valid word found to play with! Ending this game.")
                        break

                    word = match.group(1).strip()
                    question = f"What beats {word}?"
                    logging.info(f"Question: {question}")

                    ai_response = query_ai(question)
                    if not ai_response:
                        logging.error("AI Response was None, ending this game.")
                        break

                    logging.info(f"AI Response: {ai_response}")

                    input_element = driver.find_element(By.CSS_SELECTOR, "input.pl-4")
                    input_element.clear()
                    input_element.send_keys(ai_response)
                    submit_button = driver.find_element(By.CSS_SELECTOR, "button.p-4")
                    submit_button.click()

                    result = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "p.pb-2"))).text
                    logging.info(f"Result: {result}")

                    # Debugging: Log result checking
                    if "beats" in result.lower():
                        successful_beats += 1
                        logging.info(f"Incrementing successful_beats: {successful_beats}")

                    try:
                        next_button = driver.find_element(By.CSS_SELECTOR, "button.py-4")
                        next_button.click()
                    except NoSuchElementException:
                        logging.info("No 'Next' button found, attempting to click 'Play Again'.")
                        try:
                            play_again_button = driver.find_element(By.CSS_SELECTOR, "button.px-4")
                            play_again_button.click()
                            time.sleep(2)
                            break
                        except NoSuchElementException:
                            logging.error("No 'Play Again' button found. Ending game.")
                            break

                except Exception as e:
                    logging.error(f"Exception occurred: {e}")
                    break

            logging.info(f"Total Successful Beats for this game: {successful_beats}")

    finally:
        driver.quit()

if __name__ == "__main__":
    play_game()
