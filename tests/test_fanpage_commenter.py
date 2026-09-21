import pytest
import asyncio
from facebook_fanpage_commenter import FacebookFanpageCommenter

@pytest.mark.asyncio
async def test_login_with_cookie():
    commenter = FacebookFanpageCommenter(
        urls="1234567890",
        cookies_file="cookies.txt",
        comment_file="comment_list.txt",
        page_id="1234567890"
    )
    context = await commenter.login_with_cookie()
    assert context is not None
    await context.close()

@pytest.mark.asyncio
async def test_random_comment():
    commenter = FacebookFanpageCommenter(
        urls="1234567890",
        cookies_file="cookies.txt",
        comment_file="comment_list.txt",
        page_id="1234567890"
    )
    assert len(commenter.comments) > 0
    assert commenter.comments[0] != ""