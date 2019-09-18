
import time
from sys import argv
from urllib.parse import quote, unquote


def code_url(url):
    url_coded = quote(url)
    return url_coded


def decode_url(url_encoded):
    url_decoded = unquote(url_encoded)
    return url_decoded


def epoch_time_2_date(epoch_time):
    date_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(epoch_time / 1000))
    return date_str


if __name__ == "__main__":

    # try:
    #     url_encoded = str(argv[1])
    # except IndexError:

    operation = input('Operation Encode / Decode [E / D}: ')

    if operation == 'D':
        url_encoded = input('Enter url to decode:')
        url_decoded = decode_url(url_encoded)
        print(url_decoded)
    elif operation == 'E':
        url = input('Enter url to encode:')
        url_encoded = code_url(url)
        print(url_encoded)

