# -*- coding: utf-8 -*-
"""
Scrape scheduled power interruptions from KPLC website.
"""
import tempfile

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag
from requests_cache import CachedSession

from stima.exceptions import RequestError, WrongContentType

KPLC_INTERRUPTIONS_URL = "https://kplc.co.ke/category/view/50/planned-power-interruptions"


def make_request(url):
    """
    Make a GET request to the given URL.

    Params:
        url (str): URL to make a GET request to

    Raises:
        RequestError: raised when the status code is not 200

    Returns a str of the page content
    """
    # TODO: consider adding project's details in the headers.
    response = requests.get(url)
    if response.status_code != 200:
        raise RequestError(response.url, response.status_code, response.reason)

    return response.content.decode("utf-8")


def download_pdf(url):
    """
    Download the PDF file containing the power interruption details.

    Params:
        url (str): URL to download the PDF from.

    Raises:
        RequestError: raised when the status code is not 200
        WrongContentType: raised when the file fetched is not a PDF

    Returns a tuple of the PDF filename and a file object.
    """
    # content-disposition header isn't set so we do this instead
    pdf_filename = url.rsplit('/', 1)[1]
    response = requests.get(url, stream=True)
    if response.status_code != 200:
        raise RequestError(url, response.status_code, response.reason)

    # check content-type of the file is PDF
    content_type = response.headers['Content-Type']
    if content_type != "application/pdf":
        raise WrongContentType("File is not a PDF", response.url, content_type)

    # delete the temporary file once file is closed
    pdf_file_temp = tempfile.NamedTemporaryFile(delete=True)
    for chunk in response.iter_content(chunk_size=4096):
        pdf_file_temp.write(chunk)
    pdf_file_temp.seek(0)

    return pdf_filename, pdf_file_temp


def scrape_interruptions(url=None):
    """
    Scrape power interruption titles and PDF links from KPLC website.
    Params:
        url (str): URL to crawl and get titles and links from.
    Returns a dict containing the interruption title and interruption link to
    the page with the PDF to download.
    Example:
    {
        "title": "Interruptions - 20.06.2019",
        "link": "https://kplc.co.ke/content/item/3071/interruptions---20.06.2019"
    }
    """
    url = url or KPLC_INTERRUPTIONS_URL
    try:
        content = make_request(url)
    except RequestError as error:
        print("Error: {}".format(error))
        raise

    # parse content
    soup = BeautifulSoup(content, "html.parser")
    for h2_tag in soup.find("main").find_all("h2", class_='generictitle'):
        yield {
            "title": h2_tag.string,
            "link": h2_tag.a.get('href')
        }

    # go to next page
    a_tag = soup.find(
        "ul", class_="pagination").find("a", attrs={"rel": "next"})
    if isinstance(a_tag, Tag):
        next_url = a_tag.get("href")
        yield from scrape_interruptions(next_url)


def scrape_interruption_attachments(url):
    """
    Scrape power interruption link and download PDF containing interruption
    details.

    Params:
        url (str): URL that contains PDF download link(s)

    Returns a dict containing the interruption parent link, the downloaded
    file path, the download link text and the PDF download link.
    Example:
    {
        "parent_link":"https://kplc.co.ke/content/item/3071/interruptions---20.06.2019",
        "pdf_filename": "c8JP5YCE4HQ4_Interruptions - 20.06.2019.pdf",
        "pdf_file_temp": tempfile.NamedTemporaryFile(),
        "download_link_text": "Interruptions - 20.06.2019.pdf",
        "download_link": "https://kplc.co.ke/img/full/c8JP5YCE4HQ4_Interruptions%20-%2020.06.2019.pdf"
    }
    """
    try:
        content = make_request(url)
    except RequestError as error:
        print("Error: {}".format(error))
        raise

    # parse content
    soup = BeautifulSoup(content, "html.parser")
    a_tags = []
    # most of the download links are found inside anchor tags with docicon
    # class.
    attachment_div = soup.find("div", class_="attachments")
    if attachment_div:
        a_tags.extend(attachment_div.find_all("a", class_="docicon"))
    # some of the download links especially the one marked as archives, are
    # inside anchor tags with download class.
    genericintro_div = soup.find("div", class_="genericintro")
    if genericintro_div:
        a_tags.extend(genericintro_div.find_all("a", class_="download"))

    for a_tag in a_tags:
        download_link_text = a_tag.get_text()
        download_link = a_tag.get("href")

        try:
            pdf_filename, pdf_file_temp = download_pdf(download_link)
        except (RequestError, WrongContentType) as error:
            print("Error: {}".format(error))
            continue

        yield {
            "parent_link": url,
            "pdf_filename": pdf_filename,
            "pdf_file_temp": pdf_file_temp,
            "download_link_text": download_link_text,
            "download_link": download_link
        }
