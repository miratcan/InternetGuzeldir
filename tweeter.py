from dotenv import dotenv_values
from rebuild import get_lines, get_links_by_date
import pickle
import tweepy
from urllib.parse import urljoin
from tempfile import NamedTemporaryFile
import urllib.request
from openpyxl import load_workbook
from rebuild import ENV

class Tweeter:
    env = None
    document_url = None
    current_index = None
    links_sheet = None
    link_to_share = None
    api = None

    def __init__(self):
        self.check_env()

        auth = tweepy.OAuthHandler(
            ENV.get("CONSUMER_KEY"), ENV.get("CONSUMER_SECRET")
        )
        auth.set_access_token(
            ENV.get("ACCESS_TOKEN"), ENV.get("ACCESS_TOKEN_SECRET")
        )
        self.api = tweepy.API(auth)

    def check_env(self):

        if not len(ENV):
            raise Exception("are you missing something? [.env file empty!]")

        required_credentials = list(
            [
                "CONSUMER_KEY",
                "CONSUMER_SECRET",
                "ACCESS_TOKEN",
                "ACCESS_TOKEN_SECRET",
                "SITE_URL",
            ]
        )
        missing_env_fields = [
            string
            for string in required_credentials
            if string not in list(ENV.keys())
        ]
        if len(missing_env_fields):
            raise Exception(
                f"missing env credentials", format(", ".join(missing_env_fields))
            )

    def load_links(self):
        with NamedTemporaryFile(suffix=".xlsx") as spreadsheet_file:
            with urllib.request.urlopen(ENV["SPREADSHEET_URL"]) as remote_file:
                spreadsheet_file.write(remote_file.read())
                workbook = load_workbook(filename=spreadsheet_file.name,
                                         read_only=True)
        self.links_sheet = get_links_by_date(
            get_lines(workbook[ENV['SPREADSHEET_LINKS_PAGE_NAME']]), reverse=False
        )

    def create_index(self):
        self.current_index = 0
        pickle_file = {"index": str(self.current_index)}
        pickle.dump(pickle_file, open("pickle.index", "wb"))

    def load_index(self):
        try:
            pickle_file = pickle.load(open("pickle.index", "rb"))
            self.current_index = int(pickle_file["index"])
        except FileNotFoundError:
            self.create_index()

    def save_index(self):
        pickle_file = {"index": str(self.current_index)}
        pickle.dump(pickle_file, open("pickle.index", "wb"))

    def set_link_to_share(self):
        if self.current_index > len(self.links_sheet):
            raise Exception("No new links to publish")
        self.link_to_share = self.links_sheet[self.current_index]

    def get_url(self):
        return urljoin(ENV.get("SITE_URL"), self.link_to_share["file_path"])

    def tweet(self):
        tweet = self.get_url()
        print(f"Günün linki: {tweet}")
        self.api.update_status(f"Günün linki: {tweet}")


if __name__ == "__main__":
    tweeter = Tweeter()
    tweeter.load_index()
    tweeter.load_links()
    tweeter.set_link_to_share()
    tweeter.tweet()
    tweeter.current_index += 1
    tweeter.save_index()
