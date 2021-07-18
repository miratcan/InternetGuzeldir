from dotenv import dotenv_values
from rebuild import get_lines, get_links_by_date, _load_workbook, WORKBOOK_LINKS_TITLE
import pickle
import tweepy
from urllib.parse import urljoin


def load_env():
    return dotenv_values('.env')


class Tweeter:
    env = None
    document_url = None
    current_index = None
    links_sheet = None
    link_to_share = None
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

        required_credentials = list(["CONSUMER_KEY", "CONSUMER_SECRET", "ACCESS_TOKEN", "ACCESS_TOKEN_SECRET", "BASE_URL"])
        missing_env_fields = [string for string in required_credentials if string not in list(self.env.keys())]
        if len(missing_env_fields):
            raise Exception(f"missing env credentials", format(', '.join(missing_env_fields)))


    def load_links(self):
        workbook = _load_workbook()
        self.links_sheet = get_links_by_date(get_lines(workbook[WORKBOOK_LINKS_TITLE]), reverse=False)


    def create_index(self):
        self.current_index = 0
        pickle_file = {"index": str(self.current_index)}
        pickle.dump(pickle_file, open("pickle.index", "wb"))


    def load_index(self):
        try:
            pickle_file = pickle.load(open("pickle.index", "rb"))
            self.current_index = int(pickle_file['index'])
        except FileNotFoundError:
            self.create_index()


    def save_index(self):
        pickle_file = {"index": str(self.current_index)}
        pickle.dump(pickle_file, open("pickle.index", "wb"))


    def set_link_to_share(self):
        if self.current_index > len(self.links_sheet):
            raise Exception('No new links to publish')
        self.link_to_share = self.links_sheet[self.current_index]


    def get_url(self):
        return urljoin(self.env.get('BASE_URL'), self.link_to_share['file_path'])


    def tweet(self):
        tweet = self.get_url()
        print(f"daily mal: {tweet}")
        # self.api.update_status(tweet)


if __name__ == '__main__':
    tweeter = Tweeter()
    tweeter.load_index()
    tweeter.load_links()
    tweeter.set_link_to_share()
    tweeter.tweet()
    tweeter.current_index += 1
    tweeter.save_index()
