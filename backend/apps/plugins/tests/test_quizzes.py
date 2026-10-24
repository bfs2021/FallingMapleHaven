import pytest
from django.urls import reverse

from apps.notifications.models import Notification
from apps.plugins.models import Plugin
from apps.plugins.quizzes.models import (
    QuizSubmission,
    QuizSubmissionAnswer,
    QuizQuestionBank,
    QuizQuestionBankOption,
    QuizTest,
    QuizTestOption,
    QuizTestQuestion,
)


@pytest.fixture(autouse=True)
def _active_plugin(db):
    Plugin.objects.update_or_create(
        plugin_type="quiz",
        defaults={"name": "默契问答", "is_active": True},
    )


def _url(name, *args):
    return reverse(f"quiz-{name}", args=args)


def _question_payload(index, correct_order=1):
    return {
        "question_text": f"第 {index} 题更像哪一种日常？",
        "order": index,
        "correct_option_order": correct_order,
        "options": [
            {"option_text": f"选项 {index}-A", "order": 1},
            {"option_text": f"选项 {index}-B", "order": 2},
        ],
    }


def _test_payload(title="我的默契测试", count=10):
    return {
        "title": title,
        "questions": [_question_payload(index) for index in range(1, count + 1)],
    }


def _answer_payload(test, correct=True):
    answers = []
    for question in test.questions.order_by("order"):
        option = question.correct_option if correct else question.options.exclude(pk=question.correct_option_id).first()
        answers.append({"question_id": question.id, "selected_option_id": option.id})
    return {"answers": answers}


@pytest.fixture
def published_test(alice_client):
    create_resp = alice_client.post(_url("my-tests"), _test_payload(), format="json")
    test_id = create_resp.json()["data"]["id"]
    publish_resp = alice_client.post(_url("publish-test", test_id))
    assert publish_resp.status_code == 200
    return QuizTest.objects.get(pk=test_id)


class TestQuizOwnerTests:
    def test_disabled_plugin_blocks_business_endpoints(self, alice_client):
        Plugin.objects.filter(plugin_type="quiz").update(is_active=False)
        resp = alice_client.get(_url("my-tests"))
        assert resp.status_code == 404
        assert resp.json()["code"] == 40004

    def test_create_draft_allows_less_than_ten_questions(self, alice_client, alice):
        resp = alice_client.post(_url("my-tests"), _test_payload(count=2), format="json")

        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["status"] == QuizTest.Status.DRAFT
        assert data["question_count"] == 2
        assert QuizTest.objects.filter(owner=alice, title="我的默契测试").exists()

    def test_owner_max_three_non_deleted_tests(self, alice_client):
        for index in range(3):
            resp = alice_client.post(_url("my-tests"), _test_payload(title=f"测试 {index}"), format="json")
            assert resp.status_code == 201

        resp = alice_client.post(_url("my-tests"), _test_payload(title="第四套"), format="json")

        assert resp.status_code == 400
        assert resp.json()["code"] == 40005

    def test_non_owner_get_detail_returns_permission_error(self, bob_client, published_test):
        resp = bob_client.get(_url("my-test-detail", published_test.id))

        assert resp.status_code == 403
        assert resp.json()["code"] == 40003

    def test_delete_is_soft_delete(self, alice_client, published_test):
        resp = alice_client.delete(_url("my-test-detail", published_test.id))

        assert resp.status_code == 200
        published_test.refresh_from_db()
        assert published_test.status == QuizTest.Status.DELETED
        assert published_test.deleted_at is not None


class TestQuizPublish:
    def test_publish_requires_exactly_ten_questions(self, alice_client):
        create_resp = alice_client.post(_url("my-tests"), _test_payload(count=2), format="json")
        test_id = create_resp.json()["data"]["id"]

        resp = alice_client.post(_url("publish-test", test_id))

        assert resp.status_code == 400
        assert resp.json()["code"] == 40001
        assert resp.json()["data"]["errors"][0]["field"] == "questions"

    def test_publish_success_sets_published_status(self, alice_client):
        create_resp = alice_client.post(_url("my-tests"), _test_payload(), format="json")
        test_id = create_resp.json()["data"]["id"]

        resp = alice_client.post(_url("publish-test", test_id))

        assert resp.status_code == 200
        test = QuizTest.objects.get(pk=test_id)
        assert test.status == QuizTest.Status.PUBLISHED
        assert test.published_at is not None

    def test_published_test_cannot_edit_questions(self, alice_client, published_test):
        resp = alice_client.patch(
            _url("my-test-detail", published_test.id),
            {"questions": [_question_payload(1)]},
            format="json",
        )

        assert resp.status_code == 400
        assert resp.json()["code"] == 40005

    def test_publish_validates_option_count_too_few(self, alice_client):
        questions = [_question_payload(i) for i in range(1, 11)]
        questions[0]["options"] = [{"option_text": "唯一选项", "order": 1}]
        create_resp = alice_client.post(_url("my-tests"), {"title": "测试", "questions": questions}, format="json")
        assert create_resp.status_code == 201
        test_id = create_resp.json()["data"]["id"]

        resp = alice_client.post(_url("publish-test", test_id))

        assert resp.status_code == 400
        assert resp.json()["code"] == 40001
        errors = resp.json()["data"]["errors"]
        assert any("options" in e["field"] for e in errors)
        assert any("message" in e for e in errors)

    def test_publish_validates_missing_correct_answer(self, alice_client):
        questions = [_question_payload(i) for i in range(1, 11)]
        del questions[3]["correct_option_order"]
        create_resp = alice_client.post(_url("my-tests"), {"title": "测试", "questions": questions}, format="json")
        assert create_resp.status_code == 201
        test_id = create_resp.json()["data"]["id"]

        resp = alice_client.post(_url("publish-test", test_id))

        assert resp.status_code == 400
        assert resp.json()["code"] == 40001
        errors = resp.json()["data"]["errors"]
        assert any("correct_option" in e["field"] for e in errors)


class TestQuizPublicDetail:
    def test_public_detail_does_not_expose_standard_answers(self, client, published_test):
        resp = client.get(_url("public-test-detail", published_test.id))

        assert resp.status_code == 200
        question = resp.json()["data"]["questions"][0]
        assert "correct_option_id" not in question
        assert resp.cookies.get("fmh_visitor_id") is not None

    def test_public_list_marks_logged_in_submission(self, bob_client, bob, published_test):
        bob_client.post(_url("submit-test", published_test.id), _answer_payload(published_test), format="json")

        resp = bob_client.get(_url("public-tests", published_test.owner_id))


        assert resp.status_code == 200
        item = resp.json()["data"]["results"][0]
        assert item["has_submitted"] is True


class TestQuizSubmit:
    def test_logged_in_user_submit_creates_submission_answers_and_notification(self, bob_client, bob, alice, published_test):
        resp = bob_client.post(_url("submit-test", published_test.id), _answer_payload(published_test), format="json")

        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["submission"]["participant_name"] == bob.nickname
        assert data["submission"]["correct_count"] == 10
        assert data["submission"]["score_percent"] == 100.0
        submission = QuizSubmission.objects.get(pk=data["submission"]["id"])
        assert QuizSubmissionAnswer.objects.filter(submission=submission).count() == 10
        assert Notification.objects.filter(
            recipient=alice,
            sender=bob,
            notification_type=Notification.Type.PLUGIN_EVENT,
        ).exists()

    def test_visitor_submit_sets_cookie_and_does_not_create_notification(self, client, alice, published_test):
        payload = _answer_payload(published_test, correct=False)
        payload["participant_name"] = "访客"

        resp = client.post(_url("submit-test", published_test.id), payload, format="json")

        assert resp.status_code == 201
        assert resp.cookies.get("fmh_visitor_id") is not None
        submission = QuizSubmission.objects.get(pk=resp.json()["data"]["submission"]["id"])
        assert submission.participant_type == QuizSubmission.ParticipantType.VISITOR
        assert submission.visitor_token_hash
        assert submission.visitor_token_hash != resp.cookies["fmh_visitor_id"].value
        assert not Notification.objects.filter(recipient=alice).exists()

    def test_duplicate_logged_in_submit_is_rejected(self, bob_client, published_test):
        bob_client.post(_url("submit-test", published_test.id), _answer_payload(published_test), format="json")

        resp = bob_client.post(_url("submit-test", published_test.id), _answer_payload(published_test), format="json")

        assert resp.status_code == 400
        assert resp.json()["code"] == 40005
        assert "leaderboard_url" in resp.json()["data"]

    def test_owner_cannot_submit_own_test(self, alice_client, published_test):
        resp = alice_client.post(_url("submit-test", published_test.id), _answer_payload(published_test), format="json")

        assert resp.status_code == 400
        assert resp.json()["code"] == 40005

    def test_admin_cannot_submit_test(self, admin_client, published_test):
        resp = admin_client.post(_url("submit-test", published_test.id), _answer_payload(published_test), format="json")

        assert resp.status_code == 403
        assert resp.json()["code"] == 40003

    def test_invalid_answer_option_is_rejected(self, bob_client, published_test):
        payload = _answer_payload(published_test)
        other_question = QuizTestQuestion.objects.create(test=published_test, question_text="其他", order=99)
        other_option = QuizTestOption.objects.create(question=other_question, option_text="其他选项", order=1)
        payload["answers"][0]["selected_option_id"] = other_option.id
        other_question.delete()

        resp = bob_client.post(_url("submit-test", published_test.id), payload, format="json")

        assert resp.status_code == 400
        assert resp.json()["code"] == 40001

    def test_visitor_duplicate_submit_is_rejected(self, client, alice, published_test):
        payload = {**_answer_payload(published_test, correct=False), "participant_name": "访客"}

        first_resp = client.post(_url("submit-test", published_test.id), payload, format="json")
        assert first_resp.status_code == 201

        resp = client.post(_url("submit-test", published_test.id), payload, format="json")

        assert resp.status_code == 400
        assert resp.json()["code"] == 40005
        assert "leaderboard_url" in resp.json()["data"]


class TestQuizLeaderboard:
    def test_leaderboard_is_per_test_and_uses_tied_rank(self, bob_client, charlie_client, bob, charlie, published_test):
        bob_resp = bob_client.post(_url("submit-test", published_test.id), _answer_payload(published_test), format="json")
        charlie_client.post(_url("submit-test", published_test.id), _answer_payload(published_test), format="json")

        resp = bob_client.get(_url("test-leaderboard", published_test.id), {"answerId": bob_resp.json()["data"]["submission"]["id"]})

        assert resp.status_code == 200
        rows = resp.json()["data"]["leaderboard"]["results"]
        assert [row["rank"] for row in rows] == [1, 1]
        assert all(row["is_tied"] for row in rows)
        assert any(row["is_current"] for row in rows)
        assert {row["participant_name"] for row in rows} == {bob.nickname, charlie.nickname}
        assert "correct_option_id" not in rows[0]
        assert "selected_option_id" not in rows[0]

    def test_leaderboard_answer_id_must_belong_to_current_user(self, bob_client, charlie_client, bob, charlie, published_test):
        bob_resp = bob_client.post(_url("submit-test", published_test.id), _answer_payload(published_test), format="json")
        charlie_resp = charlie_client.post(_url("submit-test", published_test.id), _answer_payload(published_test, correct=False), format="json")
        bob_submission_id = bob_resp.json()["data"]["submission"]["id"]
        charlie_submission_id = charlie_resp.json()["data"]["submission"]["id"]

        resp = charlie_client.get(_url("test-leaderboard", published_test.id), {"answerId": bob_submission_id})

        assert resp.status_code == 200
        rows = resp.json()["data"]["leaderboard"]["results"]
        current_rows = [row for row in rows if row["is_current"]]
        assert len(current_rows) == 1
        assert current_rows[0]["id"] == charlie_submission_id
        assert current_rows[0]["participant_name"] == charlie.nickname

    def test_leaderboard_sorts_by_score_desc(self, bob_client, charlie_client, published_test):
        bob_client.post(_url("submit-test", published_test.id), _answer_payload(published_test, correct=False), format="json")
        charlie_client.post(_url("submit-test", published_test.id), _answer_payload(published_test), format="json")

        resp = bob_client.get(_url("test-leaderboard", published_test.id))

        scores = [row["score_percent"] for row in resp.json()["data"]["leaderboard"]["results"]]
        assert scores == [100.0, 0.0]


class TestQuizQuestionBank:
    def test_requires_authentication(self, client):
        resp = client.get(_url("question-bank"))
        assert resp.status_code == 403

    def test_tag_filter_can_combine_with_search(self, alice_client):
        daily = QuizQuestionBank.objects.create(question_text="更喜欢哪种早餐？", tags=["daily"])
        QuizQuestionBankOption.objects.bulk_create([
            QuizQuestionBankOption(bank_question=daily, option_text="豆浆", order=1),
            QuizQuestionBankOption(bank_question=daily, option_text="牛奶", order=2),
        ])
        social = QuizQuestionBank.objects.create(question_text="更喜欢哪种早餐？", tags=["social"])
        QuizQuestionBankOption.objects.bulk_create([
            QuizQuestionBankOption(bank_question=social, option_text="热闹", order=1),
            QuizQuestionBankOption(bank_question=social, option_text="安静", order=2),
        ])

        resp = alice_client.get(_url("question-bank"), {"q": "早餐", "tag": "daily"})

        assert resp.status_code == 200
        results = resp.json()["data"]["results"]
        assert [item["id"] for item in results] == [daily.id]


class TestMyQuizSubmissions:
    """GET /api/v1/plugins/quiz/my/submissions/"""

    def test_requires_authentication(self, client):
        resp = client.get(_url("my-submissions"))
        assert resp.status_code == 403

    def test_returns_only_own_submissions(self, bob_client, charlie_client, published_test):
        bob_client.post(_url("submit-test", published_test.id), _answer_payload(published_test), format="json")
        charlie_client.post(_url("submit-test", published_test.id), _answer_payload(published_test), format="json")

        resp = bob_client.get(_url("my-submissions"))

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 1
        result = data["results"][0]
        assert result["submission"]["correct_count"] == 10
        assert result["test"]["title"] == published_test.title
        assert "leaderboard_url" in result

        QuizSubmission.objects.filter(id=result["submission"]["id"]).update(is_deleted=True)
        resp = bob_client.get(_url("my-submissions"))

        assert resp.status_code == 200
        assert resp.json()["data"]["total"] == 0


class TestQuizAvailabilityGuard:
    """Draft/deleted tests must be unavailable via public endpoints."""

    def test_draft_test_not_available_via_public_detail(self, client, alice_client):
        create_resp = alice_client.post(_url("my-tests"), _test_payload(count=2), format="json")
        draft_id = create_resp.json()["data"]["id"]

        resp = client.get(_url("public-test-detail", draft_id))

        assert resp.status_code == 404
        assert resp.json()["code"] == 40004

    def test_deleted_test_not_available_via_public_detail(self, client, alice_client, published_test):
        alice_client.delete(_url("my-test-detail", published_test.id))

        resp = client.get(_url("public-test-detail", published_test.id))

        assert resp.status_code == 404
        assert resp.json()["code"] == 40004

    def test_deleted_test_excluded_from_public_list(self, client, alice_client, alice, published_test):
        alice_client.delete(_url("my-test-detail", published_test.id))

        resp = client.get(_url("public-tests", alice.id))

        assert resp.status_code == 200
        ids = [item["id"] for item in resp.json()["data"]["results"]]
        assert published_test.id not in ids

    def test_draft_test_excluded_from_public_list(self, client, alice_client, alice):
        create_resp = alice_client.post(_url("my-tests"), _test_payload(count=2), format="json")
        draft_id = create_resp.json()["data"]["id"]

        resp = client.get(_url("public-tests", alice.id))

        assert resp.status_code == 200
        ids = [item["id"] for item in resp.json()["data"]["results"]]
        assert draft_id not in ids

    def test_draft_test_not_submittable(self, client, alice_client):
        create_resp = alice_client.post(_url("my-tests"), _test_payload(count=2), format="json")
        draft_id = create_resp.json()["data"]["id"]

        resp = client.post(_url("submit-test", draft_id), {"answers": []}, format="json")

        assert resp.status_code == 404
        assert resp.json()["code"] == 40004

    def test_deleted_test_not_submittable(self, client, alice_client, published_test):
        alice_client.delete(_url("my-test-detail", published_test.id))

        resp = client.post(_url("submit-test", published_test.id), _answer_payload(published_test), format="json")

        assert resp.status_code == 404
        assert resp.json()["code"] == 40004
