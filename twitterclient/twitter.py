# -*- coding: utf-8 -*-

import json
import os
import shutil
import re
from urllib.parse import urlparse

from twitter.scraper import Scraper
from twitter.util import init_session

from lib.utils import Session
from lib.logger import logger


class TwitterClient(object):
    def __init__(self, debug=False):
        self.default_params = {'pbar': False, 'debug': 0, 'save': True}     # default params for twitter-api-scraper
        self.image_type = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.heic', '.avif'}
        self.media_type = {'.mp4', '.m4v', '.mov', '.avi', '.flv', '.mkv', '.webm'}
        self.audio_type = {'.m4a', '.mp3', '.flac', '.ogg'}
        self.size_limit = 1024**2 * 50      # Telegram bot API limit
        self.pattern = r'(?:https:\/\/)?(?:www\.)?(?:twitter|x)\.com\/(?:#!\/)?@?(\w{1,15})\/status\/(\d{1,})'
        self.debug = debug

        self.current_dir = os.getcwd()
        self.temp_dir = os.path.join(self.current_dir, 'temp')
        if not os.path.exists(self.temp_dir):
            os.mkdir(self.temp_dir)

        self.scraper = self.twitter_account()  # create scraper using session
        self.session = Session()

    def _create_scraper_from_credentials(self, email: str, username: str, password: str):
        """
        Create scraper from Twitter credentials
        NOTE: Credentials logins may be subject to risk control restrictions.
        :param email:
        :param username:
        :param password:
        :return: Twitter scraper
        """
        try:
            scraper = Scraper(email=email, username=username, password=password, **self.default_params)
            return scraper
        except Exception as e:
            logger.error('Twitter password login failed: {}'.format(e))
            return None

    def _create_scraper_from_cookies(self, cookie: dict):
        """
        Create scraper from Twitter cookies
        :param cookie: {'auth_token': 'xxx', 'ct0': 'yyy'}
        :return:
        """
        auth_token = cookie.get('auth_token', '')
        ct0 = cookie.get('ct0', '')

        if auth_token and ct0:
            try:
                scraper = Scraper(cookies=cookie, **self.default_params)
                return scraper
            except Exception as e:
                logger.error('Twitter cookie login failed: {}'.format(e))
        return None

    def twitter_account(self) -> Scraper:
        """
        Create scraper from Twitter credentials or cookies
        Get credentials from environment variables
        TWITTER_COOKIE: Please provide a json format cookie, like
            {"auth_token": "xxx", "ct0": "yyy"}

        If you don't provide any credentials, it will be created an anonymous session.
        But anonymous sessions may be flow-limited.
        :return: Twitter scraper
        """
        twitter_username = os.getenv('TWITTER_USERNAME', '')
        twitter_email = os.getenv('TWITTER_EMAIL', '')
        twitter_password = os.getenv('TWITTER_PASSWORD', '')
        twitter_cookie = os.getenv('TWITTER_COOKIE', '')

        if twitter_username and twitter_email and twitter_password:
            scraper = self._create_scraper_from_credentials(twitter_email, twitter_username, twitter_password)
            if scraper:
                logger.info('Twitter scraper created from credentials')
                return scraper

        if twitter_cookie:
            try:
                cookie = json.loads(twitter_cookie)
            except Exception as e:
                logger.error('Twitter cookie format error: {}'.format(e))
            else:
                if isinstance(cookie, dict):
                    scraper = self._create_scraper_from_cookies(cookie)
                    if scraper:
                        logger.info('Twitter scraper created from cookie')
                        return scraper

        # at last, use guest session
        session = init_session()  # initialize guest session, no login required
        logger.info('Twitter scraper created from guest session')
        return Scraper(session=session, **self.default_params)

    async def download(self, tweet_url: str) -> (list, list, str):
        """
        Download images, videos and text from tweet url
        :param tweet_url:
        :return: images_path, videos_path, text
        """
        tweet_id = self.get_tweet_id(tweet_url)
        images_url, videos_url, text = await self.get_media_url(tweet_id)
        images_path = await self.download_images(images_url, tweet_id)
        videos_path = await self.download_videos(videos_url, tweet_id)

        return images_path, videos_path, text

    def get_tweet_id(self, url: str) -> int:
        """
        Get tweet id from tweet url using regex
        :param url: https://twitter.com/elonmusk/status/1518623997054918657
        :return: 1518623997054918657
        """
        match = re.search(self.pattern, url)
        if match:
            tweet_id = match.group(2)
        else:
            raise ValueError(f'Invalid tweet url: {url}')

        return tweet_id

    async def get_tweet(self, tweet_id: int) -> dict:
        """
        Get tweet info from tweet id
        :param tweet_id:
        :return:
        """
        logger.info(f'Downloading tweet: {tweet_id}')
        tweets = await self.scraper.tweets_by_id([tweet_id])
        return tweets[0]

    async def get_largest_video(self, video_infos: list[dict]) -> str:
        """
        :param video_infos: {'url': 'https://video.twimg.com/ext_tw_video/id/pu/vid/res/name.mp4', 'bitrate': 123235}
        :return: url of the largest video and smaller than self.size_limit(Now it's 50MB)
        """
        bitrate = 0
        video_url = ''

        for video_info in video_infos:
            resp = await self.session.head(video_info['url'])
            if resp.status_code == 200:
                content_length = int(resp.headers.get('Content-Length', 0))
                if bitrate < content_length <= self.size_limit:
                    bitrate = content_length
                    video_url = video_info['url']

        return video_url

    async def get_video_url(self, video_variants: dict) -> str:
        """
        Get video url from tweet info
        Get all the video variants and choose the largest one and smaller than self.size_limit(Now it's 50MB)
        :param video_variants:
        :return:
        """
        video_infos = []
        for variant in video_variants:
            if variant.get('bitrate'):
                video_info = {'url': variant['url'], 'bitrate': variant.get('bitrate')}
                logger.debug(f'Video info: {video_info}')
                video_infos.append(video_info)

        # sort video infos by bitrate in descending order
        video_infos = sorted(video_infos, key=lambda x: x['bitrate'], reverse=True)
        logger.debug(f'Sorted video infos: {video_infos}')

        return await self.get_largest_video(video_infos)

    async def get_media_url(self, tweet_id: int) -> (list, list, str):
        """
        Get image and video url from tweet id
        :param tweet_id:
        :return:
        """
        tweet = await self.get_tweet(tweet_id)
        tweet_result = tweet['data']['tweetResult']['result']
        image_urls, video_urls, remove_urls = [], [], []
        # remove_urls is the url of the image or video in the text, we will remove it later
        text, name, screen_name = '', '', ''

        if ('legacy' in tweet_result
                and 'extended_entities' in tweet_result['legacy']
                and 'media' in tweet_result['legacy']['extended_entities']):
            for media in tweet_result['legacy']['extended_entities']['media']:
                media_type = media['type']

                if media_type == 'video':
                    video_variants = media['video_info']['variants']
                    video_url = await self.get_video_url(video_variants)
                    if video_url:
                        video_urls.append(video_url)
                        if 'url' in media:
                            remove_urls.append(media['url'])
                elif media_type == 'photo':
                    if 'media_url_https' in media:
                        image_urls.append(media['media_url_https'])
                    if 'url' in media:
                        remove_urls.append(media['url'])

        if ('core' in tweet_result
                and 'user_results' in tweet_result['core']
                and 'result' in tweet_result['core']['user_results']
                and 'legacy' in tweet_result['core']['user_results']['result']):
            user_results = tweet_result['core']['user_results']['result']['legacy']
            if 'name' in user_results:
                name = user_results['name']                 # name of the user who tweeted
            if 'screen_name' in user_results:
                screen_name = user_results['screen_name']   # screen name of the user who tweeted

        if ('note_tweet' in tweet_result
                and 'note_tweet_results' in tweet_result['note_tweet']
                and 'result' in tweet_result['note_tweet']['note_tweet_results']
                and 'text' in tweet_result['note_tweet']['note_tweet_results']['result']):
            text = tweet_result['note_tweet']['note_tweet_results']['result']['text']
        elif 'legacy' in tweet_result and 'full_text' in tweet_result['legacy']:
            text = tweet_result['legacy']['full_text']
            media_number = len(image_urls) + len(video_urls)
            if media_number > 0 and len(remove_urls) > 0:
                # if there are images or videos in the tweet, remove the url of the image or video in the text
                text = self.remove_media_link_in_text(text, remove_urls)

        if any([name, screen_name]):
            text = f'{name} ({screen_name})\n\n{text}'

        tweet_data_dir = os.path.join(self.current_dir, 'data', str(tweet_id))
        # if not debug mode, remove the tweet data directory
        if (not self.debug) and os.path.exists(tweet_data_dir) and os.path.isdir(tweet_data_dir):
            try:
                shutil.rmtree(tweet_data_dir)
            except Exception as e:
                logger.error(f'Failed to remove tweet data directory: {e}')

        return image_urls, video_urls, text

    @staticmethod
    def remove_media_link_in_text(text: str, remove_urls: [str]) -> str:
        """
        Remove the url of the image or video in the text
        :param text:
        :param remove_urls:
        :return:
        """
        logger.debug(f'text: {text}')
        logger.debug(f'Remove these urls in text: {remove_urls}')

        for remove_url in remove_urls:
            text = text.replace(remove_url, '')

        text.strip()

        return text

    async def download_images(self, images_urls: list, tweet_id: int = 0) -> list:
        """
        Download images
        :param images_urls:
        :param tweet_id:
        :return:
        """
        filename_list = []
        length = len(images_urls)

        for i in range(length):
            image_url = images_urls[i]
            logger.info(f'Downloading image: {image_url}')
            r = await self.session.get(image_url)
            if r.status_code == 200:
                filename = urlparse(image_url).path.split('/')[-1]
                filename = '{}/{}_{}_{}'.format(self.temp_dir, tweet_id, i, filename)
                with open(filename, 'wb') as f:
                    f.write(r.content)
                filename_list.append(filename)
            else:
                logger.error(f'Failed to download image: {image_url}')

        return filename_list

    async def download_videos(self, video_urls: list, tweet_id: int = 0) -> list:
        """
        Download videos
        :param video_urls:
        :param tweet_id:
        :return:
        """
        file_list = []
        length = len(video_urls)

        for i in range(length):
            video_url = video_urls[i]
            logger.info(f'Downloading video: {video_url}')
            async with self.session.stream(method='GET', url=video_url) as resp:
                filename = urlparse(video_url).path.split('/')[-1]
                filename = '{}/{}_{}_{}'.format(self.temp_dir, tweet_id, i, filename)
                with open(filename, 'wb') as f:
                    async for chunk in resp.aiter_bytes():
                        f.write(chunk)
                file_list.append(filename)

        return file_list
