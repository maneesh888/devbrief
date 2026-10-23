import subprocess
from datetime import date, timedelta

from devbrief.core import gitlog


def _git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def test_commits_for_day_finds_todays_commit(fake_repo):
    commits = gitlog.commits_for_day(str(fake_repo), date.today())
    assert len(commits) == 1
    assert commits[0]["subject"] == "Initial commit"


def test_commits_for_day_excludes_other_days(fake_repo):
    commits = gitlog.commits_for_day(str(fake_repo), date.today() - timedelta(days=5))
    assert commits == []


def test_commits_for_day_filters_by_author(fake_repo):
    _git(fake_repo, "config", "user.email", "someone-else@example.com")
    (fake_repo / "file2.txt").write_text("more\n")
    _git(fake_repo, "add", "file2.txt")
    _git(fake_repo, "commit", "-q", "-m", "Second commit")

    _git(fake_repo, "config", "user.email", "tester@example.com")
    commits = gitlog.commits_for_day(str(fake_repo), date.today())
    subjects = {c["subject"] for c in commits}
    assert subjects == {"Initial commit"}


def test_commits_for_day_dedupes_by_hash(fake_repo):
    commits = gitlog.commits_for_day(str(fake_repo), date.today())
    hashes = [c["hash"] for c in commits]
    assert len(hashes) == len(set(hashes))
