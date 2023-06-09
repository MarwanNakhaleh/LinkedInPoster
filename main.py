import os
import logging
import json

import requests

from random_selection import get_categories, get_unposted_post, get_random_choice
from helpers import dynamodb_table

logging.basicConfig(format="%(asctime)s: %(levelname)s: %(message)s")
log = logging.getLogger("LinkedInPoster")
log.setLevel(logging.INFO)

post_without_link = {
    "author": "urn:li:person:_Lng4gTp4g",
    "lifecycleState": "PUBLISHED",
    "specificContent": {
        "com.linkedin.ugc.ShareContent": {
            "shareCommentary": {
                "text": "Hello World! This is my first Share on LinkedIn!"
            },
            "shareMediaCategory": "NONE"
        }
    },
    "visibility": {
        "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
    }
}

post_with_link = {
    "author": "urn:li:person:_Lng4gTp4g",
    "lifecycleState": "PUBLISHED",
    "specificContent": {
        "com.linkedin.ugc.ShareContent": {
            "shareCommentary": {
                "text": "Learning more about LinkedIn by reading the LinkedIn Blog!"
            },
            "shareMediaCategory": "ARTICLE",
            "media": [
                {
                    "status": "READY",
                    "description": {
                        "text": "Official LinkedIn Blog - Your source for insights and information about LinkedIn."
                    },
                    "originalUrl": "https://blog.linkedin.com/",
                    "title": {
                        "text": "Official LinkedIn Blog"
                    }
                }
            ]
        }
    },
    "visibility": {
        "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
    }
}

def generate_linkedin_payload(post):
    has_link = None
    try:
        has_link = post["links"]
    except KeyError:
        pass
    try:
        only_friends = post["onlyFriends"]
    except KeyError:
        pass
    if has_link and has_link != "":
        new_post = post_with_link
        new_post["specificContent"]["com.linkedin.ugc.ShareContent"]
    else:
        new_post = post_without_link
    new_post["specificContent"]["com.linkedin.ugc.ShareContent"]["shareCommentary"]["text"] = post["content"]
    return new_post
    
def post_to_linkedin(payload):
    linkedin_request_headers = {
        "LinkedIn-Version": "X-Restli-Protocol-Version",
        "X-Restli-Protocol-Version": "2.0.0",
        "Authorization": "Bearer " + os.environ["ACCESS_TOKEN"]
    }
    r = requests.post('https://api.linkedin.com/v2/ugcPosts', headers=linkedin_request_headers, data=json.dumps(payload))
    print(r.json())
    print(r.status_code)
    return r.status_code
    
def set_has_been_posted_to_true(table, id):
    log.info("given post ID: " + id)
    table.update_item(
        Key = {
            'id': id
        },
        AttributeUpdates = {
            "hasBeenPosted": {
                "Action": "PUT", 
                "Value": "true"
            }
        }
    )
    log.info("post")

def lambda_handler(event, context):
    posts_table = dynamodb_table(os.environ["POST_TABLE"])
    categories_table = dynamodb_table(os.environ["CATEGORY_TABLE"])
    all_categories = get_categories(categories_table)
    while(len(all_categories)) > 0:
        category = get_random_choice(all_categories)
        if category != "":
            post = get_unposted_post(posts_table, category)
            try:
                post_id = post["id"]
                log.info("Retrieved post " + post_id)
                break
            except KeyError:
                all_categories.remove(category)
                log.warn("No posts available for {}".format(category))
    payload = generate_linkedin_payload(post)
    posted = post_to_linkedin(payload)
    if(posted == 201):
        set_has_been_posted_to_true(posts_table, post_id)

if __name__ == "__main__":
    linkedin_request_headers = {
        "LinkedIn-Version": "X-Restli-Protocol-Version",
        "X-Restli-Protocol-Version": "2.0.0",
        "Authorization": "Bearer " + os.environ["ACCESS_TOKEN"]
    }
    payload = generate_linkedin_payload()
    r = requests.post('https://api.linkedin.com/v2/ugcPosts', headers=linkedin_request_headers, data=payload)
    