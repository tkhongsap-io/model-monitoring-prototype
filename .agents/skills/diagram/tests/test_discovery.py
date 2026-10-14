"""The Claude Code pointers in .claude/ still point at the skill and the rule in .agents/."""

import unittest

import support

import check_diagrams

POINTER = support.REPO / ".claude" / "skills" / "diagram" / "SKILL.md"
RULE_POINTER = support.REPO / ".claude" / "rules" / "diagram.md"


class Pointers(unittest.TestCase):
    def test_the_skill_pointer_has_the_name_and_description_of_the_skill(self) -> None:
        skill = check_diagrams.frontmatter(support.SKILL / "SKILL.md")
        pointer = check_diagrams.frontmatter(POINTER)
        self.assertEqual(pointer.get("name"), skill["name"])
        self.assertEqual(pointer.get("description"), skill["description"])

    def test_the_skill_pointer_names_the_skill_file(self) -> None:
        self.assertIn(".agents/skills/diagram/SKILL.md", POINTER.read_text(encoding="utf-8"))

    def test_the_rule_pointer_imports_a_file_that_exists(self) -> None:
        imports = [
            line[1:].strip()
            for line in RULE_POINTER.read_text(encoding="utf-8").splitlines()
            if line.startswith("@")
        ]
        self.assertEqual(len(imports), 1)
        target = (RULE_POINTER.parent / imports[0]).resolve()
        self.assertEqual(target, (support.REPO / ".agents" / "rules" / "diagram.md").resolve())
        self.assertTrue(target.is_file())


if __name__ == "__main__":
    unittest.main()
