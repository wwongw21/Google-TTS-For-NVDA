from __future__ import annotations

import gettext
import re
import unittest
from html import unescape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EN_HELP = ROOT / "googleTtsForNvda" / "doc" / "en" / "readme.html"
ZH_HELP = ROOT / "googleTtsForNvda" / "doc" / "zh_CN" / "readme.html"
LOCALE_DIR = ROOT / "googleTtsForNvda" / "locale"
ZH_MANIFEST = ROOT / "googleTtsForNvda" / "locale" / "zh_CN" / "manifest.ini"


def _text(value: str) -> str:
	return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", value))).strip()


def _version_06_section(help_html: str) -> tuple[str, str]:
	match = re.search(
		r"<h3>[^<]*0\.6[^<]*</h3>\s*<ul>(.*?)</ul>",
		help_html,
		re.DOTALL | re.IGNORECASE,
	)
	if not match:
		raise AssertionError("help page is missing its Version 0.6 changelog section")
	return match.group(0), match.group(1)


class SimplifiedChineseHelpTests(unittest.TestCase):
	@classmethod
	def setUpClass(cls) -> None:
		cls.english = EN_HELP.read_text(encoding="utf-8")
		cls.chinese = ZH_HELP.read_text(encoding="utf-8")

	def test_background_readiness_matches_english_help_scope(self) -> None:
		english_settings = self.english.split("<h3>Add-on Settings</h3>", 1)[1].split("</ul>", 1)[0]
		chinese_settings = self.chinese.split("<h3>插件设置</h3>", 1)[1].split("</ul>", 1)[0]
		english_text = _text(english_settings)
		chinese_text = _text(chinese_settings)

		self.assertIn("Keep Google TTS browser runtime ready in the background", english_text)
		self.assertIn("Background browser runtime status", english_text)
		self.assertIn("在后台保持 Google TTS 浏览器运行环境就绪", chinese_text)
		self.assertIn("后台浏览器运行环境状态", chinese_text)
		self.assertIn("此设置默认关闭", chinese_text)
		self.assertIn("已关闭", chinese_text)
		self.assertIn("Google TTS 已是当前语音合成器", chinese_text)
		self.assertIn("无需另行启动后台运行环境", chinese_text)
		self.assertIn("按“确定”或“应用”后启动", chinese_text)
		self.assertIn("更多内存", chinese_text)
		self.assertIn("运行环境文件保持打开状态", chinese_text)
		self.assertIn("直到您关闭此设置或退出 NVDA", chinese_text)
		self.assertIn("按“确定”或“应用”后", chinese_text)

	def test_compiled_catalog_and_manifest_contain_current_strings(self) -> None:
		catalog = gettext.translation("nvda", localedir=str(LOCALE_DIR), languages=["zh_CN"])
		required_messages = {
			"&Keep Google TTS browser runtime ready in the background": "在后台保持 Google TTS 浏览器运行环境就绪(&K)",
			"Background browser runtime status": "后台浏览器运行环境状态",
			"Keep Google TTS browser runtime ready in the background": "在后台保持 Google TTS 浏览器运行环境就绪",
			"Off. Google TTS For NVDA will start the browser runtime only when you choose Google TTS as the current synthesizer.": "已关闭。",
			"On. Google TTS For NVDA is the current synthesizer, so no separate background browser runtime will be started.": "不会另行启动后台浏览器运行环境",
			"On. After you press OK or Apply, Google TTS For NVDA can keep the browser runtime ready in the background. This may use more memory and keep runtime files open until you turn it off or exit NVDA.": "运行环境文件保持打开状态，直到您关闭此选项或退出 NVDA。",
		}
		for source, expected in required_messages.items():
			with self.subTest(source=source):
				self.assertIn(expected, catalog.gettext(source))

		manifest = ZH_MANIFEST.read_text(encoding="utf-8")
		self.assertIn('changelog = """0.6 版本：', manifest)
		self.assertNotIn("0.5.5 版本：", manifest)

	def test_version_06_changelog_has_same_three_release_items(self) -> None:
		english_section, english_items = _version_06_section(self.english)
		chinese_section, chinese_items = _version_06_section(self.chinese)
		self.assertIn("2026-07-30", english_section)
		self.assertIn("2026-07-30", chinese_section)
		self.assertEqual(len(re.findall(r"<li>", english_items, re.IGNORECASE)), 3)
		self.assertEqual(len(re.findall(r"<li>", chinese_items, re.IGNORECASE)), 3)

		chinese_text = _text(chinese_items)
		self.assertIn("从其他语音合成器切换回来时更快准备好 Google TTS", chinese_text)
		self.assertIn("更改所选 Chromium 浏览器运行环境", chinese_text)
		self.assertIn("安装/移除语音包", chinese_text)
		self.assertIn("更新其后台准备状态", chinese_text)
		self.assertIn("提高了从 Google TTS 切换到其他语音合成器时的可靠性", chinese_text)
		self.assertLess(
			self.chinese.index("版本 0.6 (2026-07-30)"),
			self.chinese.index("版本 0.5.5(2026-07-23)"),
		)


if __name__ == "__main__":
	unittest.main()
