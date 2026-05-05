import unittest

from scripts.migrate_character_33276 import (
    build_front_matter,
    normalize_body,
    normalize_html_images,
    rewrite_ipfs_urls,
)


class MigrateCharacter33276Tests(unittest.TestCase):
    def test_normalize_body_removes_imported_h1_and_nested_front_matter(self):
        raw = """# 2020年终总结

---
title: 2020年终总结
date: 2021-02-02 18:12:32.993
updated: 2021-02-21 18:12:46.423
url: http://codelin.xyz/archives/2020-nian-zhong-zong-jie
categories:
- 杂谈
tags:
- 年终总结
---

2020对很多人来说是一定无法忘记的一年，对我更是如此
"""

        body = normalize_body("2020年终总结", raw)

        self.assertEqual(
            body,
            "2020对很多人来说是一定无法忘记的一年，对我更是如此",
        )

    def test_build_front_matter_uses_hugo_friendly_fields(self):
        front_matter = build_front_matter(
            {
                "title": "魔幻2022",
                "slug": "2022-report",
                "date": "2022-12-28T13:31:00.000Z",
                "summary": "今年是魔幻的一年",
                "tags": ["post", "年终总结"],
            }
        )

        self.assertIn('title: "魔幻2022"', front_matter)
        self.assertIn('slug: "2022-report"', front_matter)
        self.assertIn('summary: "今年是魔幻的一年"', front_matter)
        self.assertIn('tags: ["年终总结"]', front_matter)
        self.assertNotIn("cover:", front_matter)
        self.assertIn("draft: false", front_matter)

    def test_rewrite_ipfs_urls_rewrites_markdown_and_html_images(self):
        content = """![image](ipfs://Qmcua5nThgJTaa3Hiv6ev2gShKhLYPzD31LDVqH5KtwJ5e)

<img width=\"350\" src=\"ipfs://QmXhwAMxjKz6SuoRcd9cLVnNewhKMDcz4puNVfWn3uMfdT\">
"""

        rewritten = rewrite_ipfs_urls(
            content,
            {
                "Qmcua5nThgJTaa3Hiv6ev2gShKhLYPzD31LDVqH5KtwJ5e": "./attachments/Qmcua5nThgJTaa3Hiv6ev2gShKhLYPzD31LDVqH5KtwJ5e.jpeg",
                "QmXhwAMxjKz6SuoRcd9cLVnNewhKMDcz4puNVfWn3uMfdT": "./attachments/QmXhwAMxjKz6SuoRcd9cLVnNewhKMDcz4puNVfWn3uMfdT.jpeg",
            },
        )

        self.assertNotIn("ipfs://", rewritten)
        self.assertIn(
            "![image](./attachments/Qmcua5nThgJTaa3Hiv6ev2gShKhLYPzD31LDVqH5KtwJ5e.jpeg)",
            rewritten,
        )
        self.assertIn(
            '<img width="350" src="./attachments/QmXhwAMxjKz6SuoRcd9cLVnNewhKMDcz4puNVfWn3uMfdT.jpeg">',
            rewritten,
        )

    def test_normalize_html_images_converts_raw_img_to_markdown(self):
        content = """执行脚本，等待……

<img width=\"350\" src=\"./attachments/QmXhwAMxjKz6SuoRcd9cLVnNewhKMDcz4puNVfWn3uMfdT.jpeg\">
"""

        normalized = normalize_html_images(content)

        self.assertNotIn("<img", normalized)
        self.assertIn(
            "![image](./attachments/QmXhwAMxjKz6SuoRcd9cLVnNewhKMDcz4puNVfWn3uMfdT.jpeg)",
            normalized,
        )


if __name__ == "__main__":
    unittest.main()
