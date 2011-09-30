import re
from lxml import etree
from lxml.builder import E
from parsers import Parser


class Wakaba(Parser):

    features = (
        "last_modified",
    )

    def get_thread_re(self, host):
        host = re.escape(host)
        regex = r"\Ahttp://%s/[A-Za-z\d]{1,10}/res/\d{1,10}\.html\Z" % host
        return re.compile(regex)

    def get_subscription_username(self, sub):
        if sub["type"] == "thread":
            spl = sub["url"].split("/")
            thread = spl[5][:spl[5].find(".")]
            return "%s_%s_%s" % (spl[2], spl[3], thread)
        else:
            return "main"

    def do_task(self, task):
        if task["type"] != "thread":
            return
        tree = etree.HTML(task["_data"])
        posts = tree.findall(".//td[@class='reply']")
        if not posts:
            return {"last": 0}

        if "last" in task:
            # Was parsed in the past; return new posts
            updates = []
            for post_node in posts:
                post_id = self._get_post_id(post_node)
                if post_id > task["last"]:
                    updates.append(self._parse_post(post_node, task))
                    last = post_id
            if updates:
                return {"last": last, "updates": updates}
        else:
            # Wasn't parsed; return just last post's id
            last = self._get_post_id(posts[-1])
            return {"last": last}

    def _get_post_id(self, post_node):
        return int(post_node.find("a").get("name"))

    def _parse_post(self, post_node, task):
        post = {}
        label = post_node.find("label")
        title = label.find("span[@class='replytitle']")
        if title is None:
            post["title"] = ""
        else:
            post["title"] = title.text
        author_node = label.find("span[@class='commentpostername']")
        author_email_node = author_node.find("a")
        if author_email_node is None:
            post["author_email"] = ""
            post["author_name"] = author_node.text
        else:
            post["author_email"] = author_email_node.get("href")
            post["author_name"] = author_email_node.text
        if not post["author_name"]:
            post["author_name"] = ""
        trip_node = label.find("span[@class='postertrip']")
        if trip_node is None:
            post["trip_text"] = ""
            post["trip_email"] = ""
            post["date"] = author_node.tail.strip()
        else:
            trip_email_node = trip_node.find("a")
            if trip_email_node is None:
                post["trip_text"] = trip_node.text
                post["trip_email"] = ""
            else:
                post["trip_text"] = trip_email_node.text
                post["trip_email"] = trip_email_node.get("href")
            post["date"] = trip_node.tail.strip()
        post["id"] = post_node.find("a").get("name")
        filesize_node = post_node.find("span[@class='filesize']")
        if filesize_node is None:
            post["img_src"] = ""
        else:
            host = "http://" + task["host"]
            img_a = filesize_node.find("a")
            post["img_src"] = host + img_a.get("href")
            post["img_name"] = img_a.text
            post["img_size"] = filesize_node.find("em").text
            img_thumb = post_node.find(".//img[@class='thumb']")
            post["img_thumb_src"] = host + img_thumb.get("src")
        # Body
        post_body_node = post_node.find("blockquote")
        body = []
        post["body_xhtml"] = E.span()
        for node in post_body_node:
            s = ""
            tag = E.span()
            if (node.tag == "blockquote" and
                node.get("class") == "unkfunc"):
                tag.set("style", "color: #789922;")
            elif (node.tag == "pre"):
                tag.set("style", "font-family: monospace;")
                node = node[0]
            # Should be E.p() without additional brs but
            # xmpp clients processing it incorrect.
            tag.extend((E.br(), E.br()))
            if node.text:
                s += node.text
                tag[-1].tail = node.text
            # TODO: <strong><em>bold and italic</em></strong>
            for child in node:
                if child.tag == "a":
                    s += child.text
                    url = child.get("href")
                    if url.startswith("/"):
                        url = "http://" + task["host"] + url
                    tag.append(E.a(child.text, href=url))
                elif child.tag == "br":
                    s += "\n"
                    tag.append(E.br())
                elif child.tag == "strong":
                    s += "*%s*" % child.text
                    tag.append(
                        E.span(child.text, style="font-weight: bold;"))
                elif child.tag == "em":
                    s += "/%s/" % child.text
                    tag.append(
                        E.span(child.text, style="font-style: italic;"))
                elif child.tag == "del":
                    s += "-%s-" % child.text
                    tag.append(E.span(
                        child.text,
                        style="text-decoration: line-through;"))
                elif child.tag == "code":
                    s += child.text
                    tag.append(
                        E.span(child.text, style="font-family: monospace;"))
                elif child.tag == "span" and child.get("class") == "spoiler":
                    s += "%%%%%s%%%%" % child.text
                    tag.append(E.span(
                        child.text,
                        style="color: #F0D0B6; background-color: #F0D0B6;"))
                if child.tail:
                    s += child.tail
                    tag[-1].tail = child.tail
            body.append(s)
            post["body_xhtml"].append(tag)
        post["body"] = u"\n\n".join(body)
        return self._format_post(post, task)

    def _format_post(self, post, task):
        """Format post to text and xhtml representations."""
        # Text formatting
        if post["title"]:
            title = post["title"] + " "
        else:
            title = ""
        if post["author_email"]:
            email = " <%s>" % post["author_email"]
        else:
            email = ""
        post_url = task["url"] + "#" + post["id"]
        if post["img_src"]:
            img = "\nFile: %s -(%s) <%s>" % (
                post["img_name"], post["img_size"], post["img_src"])
        else:
            img = ""
        if post["body"]:
            body = "\n\n" + post["body"]
        else:
            body = ""
        text = u"%s\n%s%s%s%s %s No.%s%s%s" % (
            post_url, title, post["author_name"], post["trip_text"],
            email, post["date"], post["id"], img, body)
        # XHTML formatting
        if post["title"]:
            title = E.span(
                post["title"], " ",
                style="font-size: larger; font-weight: bold; color: #CC1105;")
        else:
            title = ""
        if post["author_name"]:
            if post["author_email"]:
                author_text = E.a(
                    post["author_name"], href=post["author_email"])
            else:
                author_text = post["author_name"]
            author = E.span(
                author_text, style="color: #117743; font-weight: bold;")
        else:
            author = ""
        if post["trip_text"]:
            if post["trip_email"]:
                trip_text = E.a(post["trip_text"], href=post["trip_email"])
            else:
                trip_text = post["trip_text"]
            trip = E.span(trip_text, style="color: #228854;")
        else:
            trip = ""
        if post["img_src"]:
            img = (
                E.br(),
                "File: ", E.a(post["img_name"], href=post["img_src"]),
                " - (", E.span(post["img_size"], style="font-style: italic;"),
                ")",
                E.br(),
                E.a(E.img(
                    alt="img", src=post["img_thumb_src"]),
                    href=post["img_src"]))
        else:
            img = ()
        xhtml_node = E.span(
            E.br(), title, author, trip,
            " ", post["date"], " ",
            E.a("No.", post["id"], href=post_url),
            *img)
        xhtml_node.append(post["body_xhtml"])
        xhtml = etree.tostring(xhtml_node, encoding=unicode)
        return (text, xhtml)


if __name__ == "__main__":
    # Test parser.
    # TODO: Use unittest/twisted.trial
    wakaba = Wakaba()
#    data = open("tests/24082.html").read()
#    task = {
#        "host": "nowere.net",
#        "url": "http://nowere.net/b/arch/24082/",
#        "type": "thread",
#        "last": 28383,
#        "_data": data,
#    }
    data = open("tests/11.html").read()
    task = {
        "host": "nowere.net",
        "url": "http://nowere.net/wa/res/1.html",
        "type": "thread",
        "last": 0,
        "_data": data,
    }
    res = wakaba.get_updates(task)
    for text, xhtml in res["updates"]:
        print text
        print "---"
        print xhtml
        print "---"
