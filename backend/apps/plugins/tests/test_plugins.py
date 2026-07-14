import pytest
from django.urls import reverse
from apps.plugins.models import Plugin


@pytest.fixture(autouse=True)
def _active_plugins(db):
    Plugin.objects.get_or_create(plugin_type="question_box", defaults={"name": "匿名提问箱", "is_active": True})
    Plugin.objects.get_or_create(plugin_type="quiz", defaults={"name": "默契问答", "is_active": True})


def _list_url():
    return reverse("plugin-list")

def _summary_url():
    return reverse("plugin-summary")

def _profile_cards_url(username_or_id):
    return reverse("profile-plugin-cards", args=[username_or_id])


class TestActivePluginsView:
    url = _list_url()

    def test_list_active_plugins(self, alice_client):
        resp = alice_client.get(self.url)
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0
        types = {p["type"] for p in data["data"]}
        assert "question_box" in types
        assert "quiz" in types

    def test_excludes_inactive_plugins(self, alice_client):
        Plugin.objects.filter(plugin_type="quiz").update(is_active=False)
        resp = alice_client.get(self.url)
        types = {p["type"] for p in resp.json()["data"]}
        assert "question_box" in types
        assert "quiz" not in types

    def test_response_structure(self, alice_client):
        resp = alice_client.get(self.url)
        for plugin in resp.json()["data"]:
            assert "type" in plugin
            assert "name" in plugin
            assert "icon" in plugin
            assert "description" in plugin

    def test_unauthenticated_blocked(self, client):
        resp = client.get(self.url)
        assert resp.status_code == 403


class TestPluginSummaryView:
    url = _summary_url()

    def test_returns_summary(self, alice_client, alice):
        resp = alice_client.get(self.url)
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0
        summaries = data["data"]
        assert len(summaries) >= 2
        summary_map = {s["type"]: s for s in summaries}
        assert "question_box" in summary_map
        assert summary_map["question_box"]["is_active"] is True

    def test_inactive_plugin_still_in_summary(self, alice_client):
        Plugin.objects.filter(plugin_type="quiz").update(is_active=False)
        resp = alice_client.get(self.url)
        summary_map = {s["type"]: s for s in resp.json()["data"]}
        assert "quiz" in summary_map
        assert summary_map["quiz"]["is_active"] is False

    def test_requires_auth(self, client):
        resp = client.get(self.url)
        assert resp.status_code == 403


class TestProfilePluginCardsView:
    def test_by_pk(self, alice_client, alice, bob):
        url = _profile_cards_url(alice.pk)
        resp = alice_client.get(url)
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0
        assert isinstance(data["data"], list)

    def test_by_username(self, alice_client, alice):
        url = _profile_cards_url(alice.username)
        resp = alice_client.get(url)
        assert resp.status_code == 200

    def test_non_existent_user(self, alice_client):
        url = _profile_cards_url(99999)
        resp = alice_client.get(url)
        assert resp.status_code == 404
        assert resp.json()["code"] == 4004

    def test_includes_guestbook_card(self, alice_client, alice):
        url = _profile_cards_url(alice.pk)
        resp = alice_client.get(url)
        types = [c["type"] for c in resp.json()["data"]]
        assert "guestbook" in types

    def test_unauthenticated_allowed(self, client, alice):
        url = _profile_cards_url(alice.pk)
        resp = client.get(url)
        assert resp.status_code == 200

    def test_inactive_plugin_excluded_from_cards(self, bob_client, bob):
        Plugin.objects.filter(plugin_type="quiz").update(is_active=False)
        url = _profile_cards_url(bob.pk)
        resp = bob_client.get(url)
        types = {c["type"] for c in resp.json()["data"]}
        assert "quiz" not in types
        assert "guestbook" in types

    def test_quiz_card_is_entry_even_without_published_tests(self, alice_client, alice, bob):
        url = _profile_cards_url(bob.pk)
        resp = alice_client.get(url)
        cards = {c["type"]: c for c in resp.json()["data"]}
        assert cards["quiz"]["route"] == f"/profile/{bob.pk}/plugins/quiz"
        assert cards["quiz"]["data"]["published_test_count"] == 0

    def test_guestbook_count(self, alice_client, alice, bob, bob_client):
        from apps.profiles.models import GuestbookEntry, UserProfile
        profile = UserProfile.objects.get(user=alice)
        GuestbookEntry.objects.create(profile=profile, author=bob, content="Hi")
        GuestbookEntry.objects.create(profile=profile, author=bob, content="Hello")
        url = _profile_cards_url(alice.pk)
        resp = alice_client.get(url)
        cards = {c["type"]: c for c in resp.json()["data"]}
        assert cards["guestbook"]["data"]["total_messages"] == 2
