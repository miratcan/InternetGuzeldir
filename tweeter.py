from dotenv import dotenv_values
import urllib.request
from openpyxl import load_workbook
from tempfile import NamedTemporaryFile
from rebuild import get_lines, get_links_by_date, DOCUMENT_URL, WORKBOOK_LINKS_TITLE
import pickle
import tweepy

BASE_URL = 'https://internetguzeldir.com/'


def load_env():
    return dotenv_values('.env')


class Tweeter:
    env = None
    document_url = None
    current_index = None
    links_sheet = None
    link = None
    api = None

    def __init__(self):
        self.load_environments()

        auth = tweepy.OAuthHandler(self.env.get('CONSUMER_KEY'), self.env.get('CONSUMER_SECRET'))
        auth.set_access_token(self.env.get('ACCESS_TOKEN'), self.env.get('ACCESS_TOKEN_SECRET'))
        self.api = tweepy.API(auth)


    def load_environments(self):
        self.env = load_env()

        if not len(self.env):
            raise Exception('are you missing something? [.env file empty!]')

        required_credentials = list(["CONSUMER_KEY", "CONSUMER_SECRET", "ACCESS_TOKEN", "ACCESS_TOKEN_SECRET"])
        missing_env_fields = [string for string in required_credentials if string not in list(self.env.keys())]
        if len(missing_env_fields):
            raise Exception(f"missing env credentials", format(', '.join(missing_env_fields)))


    def load_excel_data(self):
        temp_file = NamedTemporaryFile(suffix=".xlsx")
        temp_file.write(urllib.request.urlopen(DOCUMENT_URL).read())
        workbook = load_workbook(filename=temp_file.name, read_only=True)
        self.links_sheet = get_lines(workbook[WORKBOOK_LINKS_TITLE])


    def sort_by_created_date(self):
        sorted_links_sheet = get_links_by_date(self.links_sheet, sort_direction=False)
        self.links_sheet = sorted_links_sheet


    def create_pickle(self):
        self.current_index = 0
        pickle_file = {"index": str(self.current_index)}
        pickle.dump(pickle_file, open("pickle.index", "wb"))


    def load_pickle(self):
        try:
            pickle_file = pickle.load(open("pickle.index", "rb"))
            self.current_index = int(pickle_file['index'])
        except FileNotFoundError:
            self.create_pickle()


    def save_pickle(self):
        pickle_file = {"index": str(self.current_index)}
        pickle.dump(pickle_file, open("pickle.index", "wb"))


    def prepare_daily_link(self):
        if self.current_index > len(self.links_sheet):
            raise Exception('No new links to publish')
        self.link = self.links_sheet[self.current_index]


    def get_url(self):
        return BASE_URL + self.link['file_path']


    def tweet(self):
        tweet = self.get_url()
        print(f"daily mal: {tweet}")
        # self.api.update_status(tweet)


if __name__ == '__main__':
    tweeter = Tweeter()
    tweeter.load_pickle()
    tweeter.load_excel_data()
    tweeter.sort_by_created_date()
    tweeter.prepare_daily_link()
    tweeter.tweet()
    tweeter.current_index += 1
    tweeter.save_pickle()
