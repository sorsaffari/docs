import unittest
import glob
import re
import os
import yaml
import ast
from nested_lookup import nested_lookup

pattern_to_find_links = '(\[[^\]]*?\]\(\.\.\/)((\d+-[^\/\)]*(\/|))+)\)'
pattern_to_find_anchors = '#+\s(.*)'
pattern_to_find_template_calls = '\{%\sinclude\s.*?\s%\}'

pages = {}

# populate the `pages` dictionary with anchors and links of each
for markdown_path in glob.iglob('./**/*.md'):
    title = markdown_path.replace("./", "")

    pages[title] = {"links": [], "anchors": []}

    with open(markdown_path) as markdown_file:
        content = markdown_file.read()
        link_matches = re.findall(pattern_to_find_links, content)
        for match in link_matches:
            link = match[1]
            pages[title]["links"].append(link)

        anchor_matches = re.findall(pattern_to_find_anchors, content)
        for match in anchor_matches:
            anchor = match.replace(r"^[^a-zA-Z]+", "").replace(r" ", "-").lower()
            anchor = re.sub("[^a-zA-Z0-9 -]+", "", anchor)
            pages[title]["anchors"].append(anchor)

        template_call_matches = re.findall(pattern_to_find_template_calls, content)
        for template_call in template_call_matches:
            # page contains liquid templates. find the anchors within the .yml file used by the liquid template
            for attribute in template_call.split(" "):
                if "data=" in attribute:
                    yaml_file_path = attribute.split("=")[1]\
                                         .replace("site.data.", "")\
                                         .replace(".", "/")\
                                         .replace("_", "-") + ".yml"
                    # although the directory name is expected to have - instead of _
                    # file name is expected to have _ , so:
                    yaml_file_name = os.path.basename(yaml_file_path)
                    new_yaml_file_name = yaml_file_name.replace("-", "_")
                    yaml_file_path = yaml_file_path.replace(yaml_file_name, new_yaml_file_name)

                    yaml_content = yaml.load(open(yaml_file_path), Loader=yaml.CLoader)
                    # looks for the value of all keys named `title`, convert them to an id and add them as anchors
                    for found_title in nested_lookup("title", yaml_content):
                        anchor = found_title.replace(r" ", "-").replace(r"/", "-").lower()
                        pages[title]["anchors"].append(anchor)


class LinksTest(unittest.TestCase):

        def test_native_links(self):
            errors = []
            for title, links_and_anchors in pages.items():
                for link in links_and_anchors["links"]:
                    link_page = link.split("#")[0]
                    link_page = link_page.split("?")[0]  # removes params
                    if link_page not in pages:
                        errors.append("The link [" + link_page + "] found in [" + title + "] is broken.")

                    link_has_anchor = len(link.split("#")) > 1
                    if link_has_anchor:
                        link_anchor = link.split("#")[1]
                        if link_page in pages and link_anchor not in pages[link_page]["anchors"]:
                            errors.append("The anchor [" + link_anchor + "] of the link [" + link_page + "] found in [" + title + "] is broken.")

            self.assertEqual(len(errors), 0, msg=errors)

        def test_autolinks(self):
            errors = []
            autolink_keywords_path = "./views/autolink-keywords.js"
            # the following mappings are required because links included in autolink-keywords.js are post-processed,
            # whereas we're comparing them against raw links found in markdown files
            url_mapping = {
                "../schema/concepts": "09-schema/01-concepts.md",
                "../schema/rules": "09-schema/03-rules.md",
                "../query/match-clause": "10-query/01-match-clause.md",
                "../query/get-query": "10-query/02-get-query.md",
                "../query/insert-query": "10-query/03-insert-query.md",
                "../query/delete-query": "10-query/04-delete-query.md",
                "../query/aggregate-query": "10-query/06-aggregate-query.md",
                "../query/compute-query": "10-query/07-compute-query.md"
            }
            client_page_mapping = {
                "java": "01-java.md",
                "python": "02-python.md",
                "javascript": "03-nodejs.md",
            }

            with open(autolink_keywords_path) as autolink_keywords_file:
                content = autolink_keywords_file.read().split("codeKeywordsToLink = ")[1]
                content = re.sub(r'\/\/\s.*', '', content)  # removes comments
                autolink_keywords = ast.literal_eval(content)  # converts string to dict
                common_base_url = "03-client-api/{client}"

                for keyword in autolink_keywords["keywords"]:
                    anchor = keyword["anchor"].replace("#", "")
                    if "baseUrl" in keyword:
                        base_url = keyword["baseUrl"]
                        if url_mapping[base_url] not in pages:
                            errors.append("The link [" + base_url + "] found in [" + autolink_keywords_path + "] is broken.")
                        elif base_url in pages and anchor and anchor not in pages[base_url]["anchors"]:
                            errors.append("The anchor [" + anchor + "] of the link [" + base_url + "] found in [" + autolink_keywords_path + "] is broken.")
                    else:
                        for lang in keyword["languages"]:
                            client_url = common_base_url.replace("{client}", client_page_mapping[lang])
                            if client_url not in pages:
                                errors.append("The link [" + client_url + "] found in [" + autolink_keywords_path + "] is broken.")
                            elif client_url in pages and anchor and anchor not in pages[client_url]["anchors"]:
                                errors.append("The anchor [" + anchor + "] of the link [" + client_url + "] found in [" + autolink_keywords_path + "] is broken.")

            self.assertEqual(len(errors), 0, msg=errors)


if __name__ == '__main__':
    unittest.main()
