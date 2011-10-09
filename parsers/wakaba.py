import re
from lxml import etree
from lxml.builder import E
from parsers import Parser


class Wakaba(Parser):

    features = (
        "last_modified",
    )
    BOARD_RE = r"[A-Za-z\d]{1,10}"
    BOARD_REC = re.compile("\A%s\Z" % BOARD_RE)

    def get_thread_re(self, host):
        host = re.escape(host)
        regex = r"\Ahttp://%s/%s/res/\d{1,10}\.html\Z" % (
            host, self.BOARD_RE)
        return re.compile(regex)

    def get_board_url(self, host, board):
        if self.BOARD_REC.match(board) is not None:
            return "http://%s/%s/" % (host, board)

    def get_subscription_username(self, sub):
        if sub["type"] == "thread_updates":
            spl = sub["url"].split("/")
            thread = spl[5][:spl[5].find(".")]
            return "%s_%s_%s" % (spl[2], spl[3], thread)
        else:
            return "main"

    def do_task(self, task):
        task_handler = "task_" + task["type"]
        if hasattr(self, task_handler):
            return getattr(self, task_handler)(task)

    def task_thread_updates(self, task):
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

    def get_thread_node(self, node, is_first):
        """Placed in separate method because it
        overriden in subclass parsers.
        """
        if is_first:
            return node.find("body/form")
        else:
            return node.find("body")

    def task_board(self, task):
        # We need to do decoding by ourself because lxml
        # will not see meta charset info in page chunks.
        data = task["_data"].decode("utf-8")
        nodes = [etree.HTML(thr) for thr in data.split("<hr />")[2:-1]]
        threads = []
        is_first = True
        for node in nodes:
            thread = self.get_thread_node(node, is_first)
            is_first = False
            thread_id = self._get_post_id(thread)
            (text, xhtml) = self._parse_post(
                thread, task, is_op_post=True, show_images=False,
                render_xhtml=False, thread_id=thread_id)
            posts = thread.findall(".//td[@class='reply']")
            if posts:
                omitted_node = thread.find("span[@class='omittedposts']")
                if omitted_node is None:
                    omitted_text = ""
                    omitted_xhtml = ""
                else:
                    omitted = omitted_node.text
                    omitted = omitted[:omitted.find(".")+1].strip()
                    omitted_text = u"\n\n/%s/" % omitted
                    omitted_xhtml = E.span(
                        E.br(), E.br(),
                        omitted, style="color: #707070;")
                text += omitted_text
                xhtml = E.span(xhtml, omitted_xhtml)
                # Append 2 last posts
                for post in posts[-2:]:
                    (text2, xhtml2) = self._parse_post(
                        post, task, show_images=False,
                        render_xhtml=False, thread_id=thread_id)
                    text += "\n\n" + text2
                    xhtml.extend((E.br(), xhtml2))
            threads.append((text, self._to_s(xhtml)))
        return {"threads": threads}

    def _get_post_id(self, post_node):
        return int(post_node.find("a[@name]").get("name"))

    def _parse_post(self, post_node, task,
                    is_op_post=False, show_images=True,
                    render_xhtml=True, thread_id=None):
        post = {}
        label = post_node.find("label")
        if is_op_post:
            title_class = "filetitle"
        else:
            title_class = "replytitle"
        title = label.find("span[@class='%s']" % title_class)
        if title is None:
            post["title"] = ""
        else:
            post["title"] = title.text
        if is_op_post:
            author_node_class = "postername"
        else:
            author_node_class = "commentpostername"
        author_node = label.find("span[@class='%s']" % author_node_class)
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
        post["id"] = post_node.find("a[@name]").get("name")
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
            elif (node.tag == "div" and
                  node.get("class") == "abbrev"):
                tag.set("style", "color: #707070;")
            elif node.tag == "pre":
                tag.set("style", "font-family: monospace;")
                node = node[0]
            # Should be E.p() without additional brs but
            # xmpp clients processing it incorrect.
            tag.extend((E.br(), E.br()))
            if node.text:
                s += node.text
                tag[-1].tail = node.text
            # TODO: <strong><em>bold and italic</em></strong>
            # TODO: ul, ol
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
        return self._format_post(
            post, task, show_images, render_xhtml, thread_id)

    def _format_post(self, post, task, show_images, render_xhtml, thread_id):
        """Format post to text and xhtml representations."""
        # Text formatting
        if thread_id is None:
            url = task["url"]
        else:
            url = "%sres/%d.html" % (task["url"], thread_id)
        post_url = "%s#%s" %(url, post["id"])
        if post["title"]:
            title = post["title"] + " "
        else:
            title = ""
        if post["author_email"]:
            email = " <%s>" % post["author_email"]
        else:
            email = ""
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
            img = [
                E.br(),
                "File: ", E.a(post["img_name"], href=post["img_src"]),
                " - (", E.span(post["img_size"], style="font-style: italic;"),
                ")",
                E.br()]
            if show_images:
                img.append(
                    E.a(E.img(
                        alt="img", src=post["img_thumb_src"]),
                        href=post["img_src"]))
        else:
            img = ()
        xhtml = E.span(
            E.br(), title, author, trip,
            " ", post["date"], " ",
            E.a("No.", post["id"], href=post_url),
            *img)
        xhtml.append(post["body_xhtml"])
        if render_xhtml:
            xhtml = self._to_s(xhtml)
        return (text, xhtml)

    def _to_s(self, node):
        return etree.tostring(node, encoding=unicode)
