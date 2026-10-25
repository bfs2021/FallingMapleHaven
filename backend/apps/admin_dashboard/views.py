from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.admin_dashboard.models import SiteLog, SiteSettings
from apps.admin_dashboard.serializers import (
    AdminLogSerializer,
    AdminCommentSerializer,
    AdminPostSerializer,
    AdminSiteSettingsSerializer,
    AdminSiteSettingsUpdateSerializer,
    AdminUserSerializer,
)
from apps.common.utils import api_response, safe_int
from apps.chat.models import ChatRoom, Message
from apps.feed.models import Comment, Post
from apps.groups.models import InterestGroup, GroupMember
from apps.plugins.models import Plugin
from apps.plugins.quizzes.utils import filter_question_bank_by_tag
from apps.plugins.registry import PluginRegistry

User = get_user_model()


class AdminPermissionMixin:
    def check_admin(self, request):
        if not request.user.is_authenticated or not request.user.is_staff:
            return api_response(code=40003, message="无权访问", status=status.HTTP_403_FORBIDDEN)
        return None


def admin_paginate(queryset, request, page_size_default=20):
    page = safe_int(request.query_params.get("page"), 1)
    page_size = min(100, max(1, safe_int(request.query_params.get("page_size"), page_size_default)))
    total = queryset.count()
    start = (page - 1) * page_size
    end = start + page_size
    return page, page_size, total, queryset[start:end]


def admin_user_brief(user):
    return {
        "user_id": user.id,
        "username": user.username,
        "nickname": user.nickname,
        "avatar_url": user.avatar.url if getattr(user, "avatar", None) else None,
    }


def admin_quiz_test_data(test):
    return {
        "id": test.id,
        "owner": admin_user_brief(test.owner),
        "title": test.title,
        "status": test.status,
        "question_count": getattr(test, "question_count", None) or test.questions.count(),
        "submission_count": getattr(test, "submission_count", None) or test.submissions.filter(is_deleted=False).count(),
        "created_at": test.created_at,
        "updated_at": test.updated_at,
        "published_at": test.published_at,
        "deleted_at": test.deleted_at,
    }


def admin_quiz_question_data(question):
    return {
        "id": question.id,
        "question_type": question.question_type,
        "question_text": question.question_text,
        "order": question.order,
        "correct_option_id": question.correct_option_id,
        "source_bank_question_id": question.source_bank_question_id,
        "options": [
            {"id": option.id, "option_text": option.option_text, "order": option.order}
            for option in question.options.all().order_by("order")
        ],
    }


def admin_submission_data(submission):
    return {
        "id": submission.id,
        "test_id": submission.test_id,
        "test_title": submission.test.title,
        "owner": admin_user_brief(submission.test.owner),
        "participant_type": submission.participant_type,
        "participant_name": submission.participant_name,
        "user": admin_user_brief(submission.user) if submission.user_id else None,
        "correct_count": submission.correct_count,
        "total_count": 10,
        "score_percent": float(submission.score_percent),
        "title": submission.title,
        "is_deleted": submission.is_deleted,
        "created_at": submission.created_at,
    }


def admin_relation_match_test_data(test):
    return {
        "id": test.id,
        "slug": test.slug,
        "title": test.title,
        "status": test.status,
        "question_count": test.questions.count(),
        "created_at": test.created_at,
        "updated_at": test.updated_at,
        "published_at": test.published_at,
        "deleted_at": test.deleted_at,
    }


def admin_relation_match_question_data(question):
    return {
        "id": question.id,
        "question_type": question.question_type,
        "question_text": question.question_text,
        "scene_tag": question.scene_tag,
        "order": question.order,
        "options": [
            {
                "id": option.id,
                "option_text": option.option_text,
                "order": option.order,
                "dimension_payload": option.dimension_payload,
            }
            for option in question.options.all().order_by("order")
        ],
    }


def admin_relation_match_submission_data(submission):
    return {
        "id": submission.id,
        "test_id": submission.test_id,
        "participant_type": submission.participant_type,
        "participant_name": submission.participant_name,
        "user": admin_user_brief(submission.user) if submission.user_id else None,
        "visitor_token_hash": submission.visitor_token_hash,
        "is_deleted": submission.is_deleted,
        "created_at": submission.created_at,
    }


def admin_relation_match_profile_data(profile):
    return {
        "id": profile.id,
        "participant_type": profile.participant_type,
        "participant_name": profile.participant_name,
        "user": admin_user_brief(profile.user) if profile.user_id else None,
        "visitor_token_hash": profile.visitor_token_hash,
        "dimension_scores": profile.dimension_scores,
        "summary_text": profile.summary_text,
        "share_code": profile.share_code,
        "created_at": profile.created_at,
    }


def admin_relation_match_pair_data(pair):
    return {
        "id": pair.id,
        "relation_type": pair.relation_type,
        "subtitle": pair.subtitle,
        "profile_a": admin_relation_match_profile_data(pair.profile_a),
        "profile_b": admin_relation_match_profile_data(pair.profile_b),
        "summary_a": pair.summary_a,
        "summary_b": pair.summary_b,
        "role_a": pair.role_a,
        "role_b": pair.role_b,
        "dimension_compare": pair.dimension_compare,
        "relation_explain": pair.relation_explain,
        "highlight_text": pair.highlight_text,
        "advice_text": pair.advice_text,
        "created_at": pair.created_at,
    }


class AdminUserListView(APIView, AdminPermissionMixin):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        error = self.check_admin(request)
        if error:
            return error

        search = request.query_params.get("search", "").strip()
        users = User.objects.all()
        if search:
            if search.isdigit():
                # The search box promises lookup by ID; a numeric query is
                # that lookup, not a substring match over names and emails.
                users = users.filter(id=int(search))
            else:
                users = users.filter(
                    Q(username__icontains=search)
                    | Q(nickname__icontains=search)
                    | Q(email__icontains=search)
                )
        users = users.order_by("-date_joined")
        page = safe_int(request.query_params.get("page"), 1)
        page_size = 20
        total = users.count()
        start = (page - 1) * page_size
        end = start + page_size
        page_users = users[start:end]
        serializer = AdminUserSerializer(page_users, many=True)
        return api_response(data={
            "total": total,
            "page": page,
            "page_size": page_size,
            "results": serializer.data,
        })


class AdminUserUpdateView(APIView, AdminPermissionMixin):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        error = self.check_admin(request)
        if error:
            return error

        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return api_response(code=40004, message="用户不存在", status=status.HTTP_404_NOT_FOUND)

        allowed_fields = {"is_active"}
        if request.user.is_superuser:
            allowed_fields.add("is_staff")
        updates = {key: value for key, value in request.data.items() if key in allowed_fields}
        for key, value in updates.items():
            setattr(user, key, value)
        user.save()

        SiteLog.objects.create(
            user=request.user,
            action="update_user",
            detail={"user_id": pk, "changes": request.data},
            ip_address=request.META.get("REMOTE_ADDR"),
        )

        return api_response(data=AdminUserSerializer(user).data)


class AdminPostListView(APIView, AdminPermissionMixin):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        error = self.check_admin(request)
        if error:
            return error

        posts = Post.objects.select_related("author").all().order_by("-created_at")
        page = safe_int(request.query_params.get("page"), 1)
        page_size = 20
        total = posts.count()
        start = (page - 1) * page_size
        end = start + page_size
        page_posts = posts[start:end]
        serializer = AdminPostSerializer(page_posts, many=True)
        return api_response(data={
            "total": total,
            "page": page,
            "page_size": page_size,
            "results": serializer.data,
        })


class AdminPostDeleteView(APIView, AdminPermissionMixin):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        error = self.check_admin(request)
        if error:
            return error

        try:
            post = Post.objects.get(pk=pk)
        except Post.DoesNotExist:
            return api_response(code=40004, message="动态不存在", status=status.HTTP_404_NOT_FOUND)

        post.delete()

        SiteLog.objects.create(
            user=request.user,
            action="delete_post",
            detail={"post_id": pk},
            ip_address=request.META.get("REMOTE_ADDR"),
        )

        return api_response(message="动态已删除")


class AdminCommentListView(APIView, AdminPermissionMixin):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        error = self.check_admin(request)
        if error:
            return error

        comments = Comment.objects.select_related("author", "post").order_by("-created_at")
        page = safe_int(request.query_params.get("page"), 1)
        page_size = 20
        total = comments.count()
        start = (page - 1) * page_size
        end = start + page_size
        page_comments = comments[start:end]
        serializer = AdminCommentSerializer(page_comments, many=True)
        return api_response(data={
            "total": total,
            "page": page,
            "page_size": page_size,
            "results": serializer.data,
        })


class AdminCommentDeleteView(APIView, AdminPermissionMixin):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        error = self.check_admin(request)
        if error:
            return error

        try:
            comment = Comment.objects.get(pk=pk)
        except Comment.DoesNotExist:
            return api_response(code=40004, message="评论不存在", status=status.HTTP_404_NOT_FOUND)

        comment.delete()

        SiteLog.objects.create(
            user=request.user,
            action="delete_comment",
            detail={"comment_id": pk},
            ip_address=request.META.get("REMOTE_ADDR"),
        )

        return api_response(message="评论已删除")


class AdminAnonymousQuestionsView(APIView, AdminPermissionMixin):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        error = self.check_admin(request)
        if error:
            return error

        from apps.plugins.questions.models import AnonymousQuestion
        from apps.plugins.questions.serializers import AdminQuestionSerializer
        questions = AnonymousQuestion.objects.select_related("recipient", "sender").all().order_by("-created_at")
        page = safe_int(request.query_params.get("page"), 1)
        page_size = 20
        total = questions.count()
        start = (page - 1) * page_size
        end = start + page_size
        page_questions = questions[start:end]
        serializer = AdminQuestionSerializer(page_questions, many=True)
        return api_response(data={
            "total": total,
            "page": page,
            "page_size": page_size,
            "results": serializer.data,
        })


class AdminQuizTestListView(APIView, AdminPermissionMixin):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        error = self.check_admin(request)
        if error:
            return error

        from apps.plugins.quizzes.models import QuizTest

        tests = QuizTest.objects.select_related("owner").annotate(
            question_count=Count("questions", distinct=True),
            submission_count=Count("submissions", filter=Q(submissions__is_deleted=False), distinct=True),
        )
        status_param = request.query_params.get("status")
        if status_param:
            tests = tests.filter(status=status_param)
        owner_id = request.query_params.get("owner_id")
        if owner_id:
            tests = tests.filter(owner_id=owner_id)
        q = request.query_params.get("q", "").strip()
        if q:
            tests = tests.filter(Q(title__icontains=q) | Q(owner__username__icontains=q) | Q(owner__nickname__icontains=q))
        tests = tests.order_by("-created_at")

        page, page_size, total, page_tests = admin_paginate(tests, request)
        data = [admin_quiz_test_data(test) for test in page_tests]
        return api_response(data={
            "total": total,
            "page": page,
            "page_size": page_size,
            "results": data,
        })


class AdminQuizTestDetailView(APIView, AdminPermissionMixin):
    permission_classes = [IsAuthenticated]

    def get_object(self, test_id):
        from apps.plugins.quizzes.models import QuizTest

        return QuizTest.objects.select_related("owner").prefetch_related("questions__options").filter(pk=test_id).first()

    def get(self, request, test_id):
        error = self.check_admin(request)
        if error:
            return error
        test = self.get_object(test_id)
        if not test:
            return api_response(code=40004, message="测试不存在", status=status.HTTP_404_NOT_FOUND)
        data = admin_quiz_test_data(test)
        data["questions"] = [admin_quiz_question_data(question) for question in test.questions.all().order_by("order")]
        return api_response(data=data)

    def delete(self, request, test_id):
        error = self.check_admin(request)
        if error:
            return error
        test = self.get_object(test_id)
        if not test:
            return api_response(code=40004, message="测试不存在", status=status.HTTP_404_NOT_FOUND)
        from apps.plugins.quizzes.models import QuizTest

        test.status = QuizTest.Status.DELETED
        test.deleted_at = timezone.now()
        test.save(update_fields=["status", "deleted_at", "updated_at"])
        SiteLog.objects.create(
            user=request.user,
            action="delete_quiz_test",
            detail={"test_id": test.id, "title": test.title},
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return api_response(message="测试已删除")


class AdminQuizSubmissionListView(APIView, AdminPermissionMixin):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        error = self.check_admin(request)
        if error:
            return error

        from apps.plugins.quizzes.models import QuizSubmission

        submissions = QuizSubmission.objects.select_related("test", "test__owner", "user")
        test_id = request.query_params.get("test_id")
        if test_id:
            submissions = submissions.filter(test_id=test_id)
        owner_id = request.query_params.get("owner_id")
        if owner_id:
            submissions = submissions.filter(test__owner_id=owner_id)
        participant_type = request.query_params.get("participant_type")
        if participant_type:
            submissions = submissions.filter(participant_type=participant_type)
        submissions = submissions.order_by("-created_at")
        page, page_size, total, page_submissions = admin_paginate(submissions, request)
        return api_response(data={
            "total": total,
            "page": page,
            "page_size": page_size,
            "results": [admin_submission_data(item) for item in page_submissions],
        })


class AdminQuizSubmissionDetailView(APIView, AdminPermissionMixin):
    permission_classes = [IsAuthenticated]

    def get_object(self, submission_id):
        from apps.plugins.quizzes.models import QuizSubmission

        return QuizSubmission.objects.select_related("test", "test__owner", "user").prefetch_related(
            "answers__question__options",
            "answers__selected_option",
        ).filter(pk=submission_id).first()

    def get(self, request, submission_id):
        error = self.check_admin(request)
        if error:
            return error
        submission = self.get_object(submission_id)
        if not submission:
            return api_response(code=40004, message="答卷不存在", status=status.HTTP_404_NOT_FOUND)
        data = admin_submission_data(submission)
        data["test"] = {"id": submission.test_id, "title": submission.test.title, "owner": admin_user_brief(submission.test.owner)}
        data["answers"] = []
        for answer in submission.answers.all().order_by("question__order"):
            question_data = admin_quiz_question_data(answer.question)
            data["answers"].append({
                "id": answer.id,
                "question": question_data,
                "question_id": answer.question_id,
                "question_text": answer.question.question_text,
                "options": question_data["options"],
                "selected_option_id": answer.selected_option_id,
                "correct_option_id": answer.question.correct_option_id,
                "is_correct": answer.is_correct,
            })
        return api_response(data=data)

    def delete(self, request, submission_id):
        error = self.check_admin(request)
        if error:
            return error
        submission = self.get_object(submission_id)
        if not submission:
            return api_response(code=40004, message="答卷不存在", status=status.HTTP_404_NOT_FOUND)
        submission.is_deleted = True
        submission.save(update_fields=["is_deleted"])
        SiteLog.objects.create(
            user=request.user,
            action="delete_quiz_submission",
            detail={"submission_id": submission.id, "test_id": submission.test_id},
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return api_response(message="答卷已删除")


class AdminQuizQuestionBankListCreateView(APIView, AdminPermissionMixin):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        error = self.check_admin(request)
        if error:
            return error
        from apps.plugins.quizzes.serializers import QuizBankQuestionSerializer
        from apps.plugins.quizzes.models import QuizQuestionBank

        questions = QuizQuestionBank.objects.prefetch_related("options").order_by("-created_at")
        q = request.query_params.get("q", "").strip()
        if q:
            questions = questions.filter(question_text__icontains=q)
        tag = request.query_params.get("tag", "").strip()
        questions = filter_question_bank_by_tag(questions, tag)
        page, page_size, total, page_questions = admin_paginate(questions, request)
        return api_response(data={
            "total": total,
            "page": page,
            "page_size": page_size,
            "results": QuizBankQuestionSerializer(page_questions, many=True).data,
        })

    def post(self, request):
        error = self.check_admin(request)
        if error:
            return error
        question, response = save_bank_question(request.data)
        if response:
            return response
        SiteLog.objects.create(
            user=request.user,
            action="create_quiz_bank_question",
            detail={"question_id": question.id},
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        from apps.plugins.quizzes.serializers import QuizBankQuestionSerializer

        return api_response(data=QuizBankQuestionSerializer(question).data, status=status.HTTP_201_CREATED)


class AdminQuizQuestionBankDetailView(APIView, AdminPermissionMixin):
    permission_classes = [IsAuthenticated]

    def patch(self, request, question_id):
        error = self.check_admin(request)
        if error:
            return error
        from apps.plugins.quizzes.models import QuizQuestionBank
        from apps.plugins.quizzes.serializers import QuizBankQuestionSerializer

        question = QuizQuestionBank.objects.filter(pk=question_id).first()
        if not question:
            return api_response(code=40004, message="题库题不存在", status=status.HTTP_404_NOT_FOUND)
        question, response = save_bank_question(request.data, question)
        if response:
            return response
        SiteLog.objects.create(
            user=request.user,
            action="update_quiz_bank_question",
            detail={"question_id": question.id},
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return api_response(data=QuizBankQuestionSerializer(question).data)

    def delete(self, request, question_id):
        error = self.check_admin(request)
        if error:
            return error
        from apps.plugins.quizzes.models import QuizQuestionBank

        question = QuizQuestionBank.objects.filter(pk=question_id).first()
        if not question:
            return api_response(code=40004, message="题库题不存在", status=status.HTTP_404_NOT_FOUND)
        detail = {"question_id": question.id, "question_text": question.question_text}
        question.delete()
        SiteLog.objects.create(
            user=request.user,
            action="delete_quiz_bank_question",
            detail=detail,
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return api_response(message="题库题已删除")


class AdminQuizStatsView(APIView, AdminPermissionMixin):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        error = self.check_admin(request)
        if error:
            return error
        from apps.plugins.quizzes.models import QuizQuestionBank, QuizSubmission, QuizTest

        return api_response(data={
            "total_tests": QuizTest.objects.count(),
            "published_tests": QuizTest.objects.filter(status=QuizTest.Status.PUBLISHED).count(),
            "draft_tests": QuizTest.objects.filter(status=QuizTest.Status.DRAFT).count(),
            "deleted_tests": QuizTest.objects.filter(status=QuizTest.Status.DELETED).count(),
            "total_submissions": QuizSubmission.objects.filter(is_deleted=False).count(),
            "user_submissions": QuizSubmission.objects.filter(is_deleted=False, participant_type=QuizSubmission.ParticipantType.USER).count(),
            "visitor_submissions": QuizSubmission.objects.filter(is_deleted=False, participant_type=QuizSubmission.ParticipantType.VISITOR).count(),
            "question_bank_count": QuizQuestionBank.objects.count(),
        })


class AdminRelationMatchTestListView(APIView, AdminPermissionMixin):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        error = self.check_admin(request)
        if error:
            return error

        from apps.plugins.relation_match.models import RelationMatchTest

        tests = RelationMatchTest.objects.prefetch_related("questions").order_by("-created_at")
        page, page_size, total, page_tests = admin_paginate(tests, request)
        return api_response(data={
            "total": total,
            "page": page,
            "page_size": page_size,
            "results": [admin_relation_match_test_data(item) for item in page_tests],
        })


class AdminRelationMatchTestDetailView(APIView, AdminPermissionMixin):
    permission_classes = [IsAuthenticated]

    def get(self, request, test_id):
        error = self.check_admin(request)
        if error:
            return error

        from apps.plugins.relation_match.models import RelationMatchTest

        test = RelationMatchTest.objects.prefetch_related("questions__options").filter(pk=test_id).first()
        if not test:
            return api_response(code=40004, message="测试不存在", status=status.HTTP_404_NOT_FOUND)

        data = admin_relation_match_test_data(test)
        data["questions"] = [admin_relation_match_question_data(item) for item in test.questions.all().order_by("order")]
        return api_response(data=data)


class AdminRelationMatchSubmissionListView(APIView, AdminPermissionMixin):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        error = self.check_admin(request)
        if error:
            return error

        from apps.plugins.relation_match.models import RelationMatchTestAnswer

        submissions = RelationMatchTestAnswer.objects.select_related("test", "user").order_by("-created_at")
        page, page_size, total, page_submissions = admin_paginate(submissions, request)
        return api_response(data={
            "total": total,
            "page": page,
            "page_size": page_size,
            "results": [admin_relation_match_submission_data(item) for item in page_submissions],
        })


class AdminRelationMatchSubmissionDetailView(APIView, AdminPermissionMixin):
    permission_classes = [IsAuthenticated]

    def get(self, request, submission_id):
        error = self.check_admin(request)
        if error:
            return error

        from apps.plugins.relation_match.models import RelationMatchTestAnswer

        submission = RelationMatchTestAnswer.objects.select_related("test", "user").prefetch_related("items__question__options").filter(pk=submission_id).first()
        if not submission:
            return api_response(code=40004, message="答卷不存在", status=status.HTTP_404_NOT_FOUND)

        data = admin_relation_match_submission_data(submission)
        answers = []
        for item in submission.items.all().order_by("question__order"):
            question = item.question
            option_text_map = {
                option.id: option.option_text
                for option in question.options.all().order_by("order")
            }
            selected_options = item.selected_options
            if not isinstance(selected_options, list):
                selected_options = [selected_options]
            answers.append({
                "id": item.id,
                "question_id": item.question_id,
                "question_text": question.question_text,
                "question_type": question.question_type,
                "selected_options": item.selected_options,
                "selected_option_texts": [option_text_map.get(option_id, "") for option_id in selected_options],
                "dimension_payload": item.dimension_payload,
            })
        data["answers"] = answers
        return api_response(data=data)


class AdminRelationMatchProfileListView(APIView, AdminPermissionMixin):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        error = self.check_admin(request)
        if error:
            return error

        from apps.plugins.relation_match.models import RelationMatchProfile

        profiles = RelationMatchProfile.objects.select_related("user", "test").order_by("-created_at")
        page, page_size, total, page_profiles = admin_paginate(profiles, request)
        return api_response(data={
            "total": total,
            "page": page,
            "page_size": page_size,
            "results": [admin_relation_match_profile_data(item) for item in page_profiles],
        })


class AdminRelationMatchPairListView(APIView, AdminPermissionMixin):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        error = self.check_admin(request)
        if error:
            return error

        from apps.plugins.relation_match.models import RelationMatchPairResult

        pairs = RelationMatchPairResult.objects.select_related("profile_a", "profile_b").order_by("-created_at")
        page, page_size, total, page_pairs = admin_paginate(pairs, request)
        return api_response(data={
            "total": total,
            "page": page,
            "page_size": page_size,
            "results": [admin_relation_match_pair_data(item) for item in page_pairs],
        })


class AdminRelationMatchStatsView(APIView, AdminPermissionMixin):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        error = self.check_admin(request)
        if error:
            return error

        from apps.plugins.relation_match.models import RelationMatchPairResult, RelationMatchProfile, RelationMatchTest, RelationMatchTestAnswer

        return api_response(data={
            "total_tests": RelationMatchTest.objects.count(),
            "published_tests": RelationMatchTest.objects.filter(status=RelationMatchTest.Status.PUBLISHED).count(),
            "total_profiles": RelationMatchProfile.objects.count(),
            "user_profiles": RelationMatchProfile.objects.filter(participant_type=RelationMatchProfile.ParticipantType.USER).count(),
            "visitor_profiles": RelationMatchProfile.objects.filter(participant_type=RelationMatchProfile.ParticipantType.VISITOR).count(),
            "total_submissions": RelationMatchTestAnswer.objects.filter(is_deleted=False).count(),
            "user_submissions": RelationMatchTestAnswer.objects.filter(is_deleted=False, participant_type=RelationMatchTestAnswer.ParticipantType.USER).count(),
            "visitor_submissions": RelationMatchTestAnswer.objects.filter(is_deleted=False, participant_type=RelationMatchTestAnswer.ParticipantType.VISITOR).count(),
            "total_pairs": RelationMatchPairResult.objects.count(),
        })


def save_bank_question(data, question=None):
    from apps.plugins.quizzes.models import QuizQuestionBank, QuizQuestionBankOption

    question_text = str(data.get("question_text", "")).strip()
    if not question_text or len(question_text) > 80:
        return None, api_response(code=40001, message="题目不能为空且不超过 80 个字符", status=status.HTTP_400_BAD_REQUEST)
    options = data.get("options") or []
    if not (2 <= len(options) <= 4):
        return None, api_response(code=40001, message="题库题必须有 2-4 个选项", status=status.HTTP_400_BAD_REQUEST)
    normalized_options = []
    for index, option in enumerate(options):
        option_text = str(option.get("option_text", "")).strip()
        if not option_text or len(option_text) > 30:
            return None, api_response(code=40001, message="选项不能为空且不超过 30 个字符", status=status.HTTP_400_BAD_REQUEST)
        normalized_options.append({"option_text": option_text, "order": index + 1})
    tags = data.get("tags") or []
    if not isinstance(tags, list):
        return None, api_response(code=40001, message="标签格式错误", status=status.HTTP_400_BAD_REQUEST)
    with transaction.atomic():
        if question is None:
            question = QuizQuestionBank.objects.create(question_text=question_text, tags=tags)
        else:
            question.question_text = question_text
            question.tags = tags
            question.save(update_fields=["question_text", "tags", "updated_at"])
            question.options.all().delete()
        QuizQuestionBankOption.objects.bulk_create([
            QuizQuestionBankOption(bank_question=question, **option)
            for option in normalized_options
        ])
    return question, None


class AdminPluginListView(APIView, AdminPermissionMixin):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        error = self.check_admin(request)
        if error:
            return error

        plugins = Plugin.objects.all().order_by("id")
        page = safe_int(request.query_params.get("page"), 1)
        page_size = 20
        total = plugins.count()
        start = (page - 1) * page_size
        end = start + page_size
        page_plugins = plugins[start:end]
        data = [
            {
                "id": p.id,
                "name": p.name,
                "type": p.plugin_type,
                "is_active": p.is_active,
                "config": p.config,
                "created_at": p.created_at,
            }
            for p in page_plugins
        ]
        return api_response(data={
            "total": total,
            "page": page,
            "page_size": page_size,
            "results": data,
        })


class AdminPluginUpdateView(APIView, AdminPermissionMixin):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        error = self.check_admin(request)
        if error:
            return error

        try:
            plugin = Plugin.objects.get(pk=pk)
        except Plugin.DoesNotExist:
            return api_response(code=40004, message="插件不存在", status=status.HTTP_404_NOT_FOUND)

        is_active = request.data.get("is_active")
        if is_active is not None:
            plugin.is_active = is_active
            plugin.save()

        SiteLog.objects.create(
            user=request.user,
            action="update_plugin",
            detail={"plugin_id": pk, "is_active": is_active},
            ip_address=request.META.get("REMOTE_ADDR"),
        )

        return api_response(data={
            "id": plugin.id,
            "name": plugin.name,
            "type": plugin.plugin_type,
            "is_active": plugin.is_active,
            "config": plugin.config,
            "created_at": plugin.created_at,
        })


class AdminSettingsView(APIView, AdminPermissionMixin):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        error = self.check_admin(request)
        if error:
            return error

        settings = SiteSettings.objects.all()
        serializer = AdminSiteSettingsSerializer(settings, many=True)
        return api_response(data=serializer.data)

    def patch(self, request):
        error = self.check_admin(request)
        if error:
            return error

        serializer = AdminSiteSettingsUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        settings_data = serializer.validated_data["settings"]
        for key, value in settings_data.items():
            SiteSettings.objects.update_or_create(key=key, defaults={"value": value})

        SiteLog.objects.create(
            user=request.user,
            action="update_settings",
            detail={"settings": settings_data},
            ip_address=request.META.get("REMOTE_ADDR"),
        )

        settings = SiteSettings.objects.all()
        out_serializer = AdminSiteSettingsSerializer(settings, many=True)
        return api_response(data=out_serializer.data)


class AdminStatsView(APIView, AdminPermissionMixin):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        error = self.check_admin(request)
        if error:
            return error

        data = {
            "total_users": User.objects.count(),
            "total_posts": Post.objects.count(),
            "total_comments": Comment.objects.count(),
            "total_messages": Message.objects.count(),
            "active_users_today": User.objects.filter(last_login__date__gte=timezone.now().date()).count(),
        }
        return api_response(data=data)


class AdminPluginConfigView(APIView, AdminPermissionMixin):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        error = self.check_admin(request)
        if error:
            return error

        configs = []
        for plugin in PluginRegistry.get_all_plugins().values():
            admin_config = plugin.get_admin_config()
            if admin_config and admin_config.get("sidebar"):
                configs.append({
                    "type": plugin.plugin_type,
                    "name": plugin.display_name,
                    **admin_config,
                })
        return api_response(data=configs)


class AdminLogsView(APIView, AdminPermissionMixin):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        error = self.check_admin(request)
        if error:
            return error

        logs = SiteLog.objects.select_related("user").all()

        action = request.query_params.get("action", "").strip()
        if action:
            logs = logs.filter(action=action)

        user_id = safe_int(request.query_params.get("user_id"), None)
        if user_id is not None:
            logs = logs.filter(user_id=user_id)

        logs = logs.order_by("-created_at")

        page = safe_int(request.query_params.get("page"), 1)
        page_size = 50
        total = logs.count()
        start = (page - 1) * page_size
        end = start + page_size
        page_logs = logs[start:end]

        serializer = AdminLogSerializer(page_logs, many=True)
        return api_response(data={
            "total": total,
            "page": page,
            "page_size": page_size,
            "results": serializer.data,
        })


class AdminLogActionsView(APIView, AdminPermissionMixin):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        error = self.check_admin(request)
        if error:
            return error
        actions = SiteLog.objects.values_list("action", flat=True).distinct().order_by("action")
        return api_response(data=list(actions))


class AdminTrendsView(APIView, AdminPermissionMixin):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        error = self.check_admin(request)
        if error:
            return error

        from django.utils import timezone
        from django.db.models import Count
        from django.db.models.functions import TruncDate
        from apps.feed.models import Post
        from apps.accounts.models import User

        days = safe_int(request.query_params.get("days"), 7)
        since = timezone.now() - timezone.timedelta(days=days)

        user_trends = (
            User.objects.filter(date_joined__gte=since)
            .annotate(date=TruncDate("date_joined"))
            .values("date")
            .annotate(count=Count("id"))
            .order_by("date")
        )

        post_trends = (
            Post.objects.filter(created_at__gte=since)
            .annotate(date=TruncDate("created_at"))
            .values("date")
            .annotate(count=Count("id"))
            .order_by("date")
        )

        from apps.chat.models import Message
        from apps.feed.models import Comment
        from apps.profiles.models import VisitRecord
        from apps.friends.models import Friendship

        msg_trends = (
            Message.objects.filter(created_at__gte=since)
            .annotate(date=TruncDate("created_at"))
            .values("date")
            .annotate(count=Count("id"))
            .order_by("date")
        )

        comment_trends = (
            Comment.objects.filter(created_at__gte=since)
            .annotate(date=TruncDate("created_at"))
            .values("date")
            .annotate(count=Count("id"))
            .order_by("date")
        )

        visit_trends = (
            VisitRecord.objects.filter(visited_at__gte=since)
            .annotate(date=TruncDate("visited_at"))
            .values("date")
            .annotate(count=Count("id"))
            .order_by("date")
        )

        friend_trends = (
            Friendship.objects.filter(created_at__gte=since)
            .annotate(date=TruncDate("created_at"))
            .values("date")
            .annotate(count=Count("id"))
            .order_by("date")
        )

        return api_response(data={
            "days": days,
            "users": list(user_trends),
            "posts": list(post_trends),
            "messages": list(msg_trends),
            "comments": list(comment_trends),
            "visits": list(visit_trends),
            "friendships": list(friend_trends),
        })


class AdminGroupListView(APIView, AdminPermissionMixin):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        error = self.check_admin(request)
        if error:
            return error

        groups = InterestGroup.objects.select_related("creator").annotate(member_count=Count('members'))
        search = request.query_params.get("search", "").strip()
        if search:
            groups = groups.filter(name__icontains=search)
        groups = groups.order_by("-created_at")

        page = safe_int(request.query_params.get("page"), 1)
        page_size = 20
        total = groups.count()
        start = (page - 1) * page_size
        end = start + page_size
        page_groups = groups[start:end]

        data = []
        for g in page_groups:
            data.append({
                "id": g.id,
                "name": g.name,
                "description": g.description,
                "cover_url": g.cover_image.url if g.cover_image else None,
                "is_public": g.is_public,
                "creator_name": g.creator.nickname,
                "member_count": g.member_count,
                "created_at": g.created_at,
            })
        return api_response(data={
            "total": total,
            "page": page,
            "page_size": page_size,
            "results": data,
        })


class AdminGroupDeleteView(APIView, AdminPermissionMixin):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        error = self.check_admin(request)
        if error:
            return error

        try:
            group = InterestGroup.objects.get(pk=pk)
        except InterestGroup.DoesNotExist:
            return api_response(code=40004, message="小组不存在", status=status.HTTP_404_NOT_FOUND)

        group_info = {"id": group.id, "name": group.name, "creator": group.creator.nickname}

        GroupMember.objects.filter(group=group).delete()
        ChatRoom.objects.filter(group_id=pk).delete()
        Post.objects.filter(group_id=pk).update(group=None)
        group.delete()

        SiteLog.objects.create(
            user=request.user,
            action="delete_group",
            detail=group_info,
            ip_address=request.META.get("REMOTE_ADDR"),
        )

        return api_response(message="小组已删除")


class AdminGroupPostsView(APIView, AdminPermissionMixin):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        error = self.check_admin(request)
        if error:
            return error

        try:
            group = InterestGroup.objects.get(pk=pk)
        except InterestGroup.DoesNotExist:
            return api_response(code=40004, message="小组不存在", status=status.HTTP_404_NOT_FOUND)

        posts = Post.objects.filter(group_id=pk).select_related('author').order_by("-created_at")

        page = safe_int(request.query_params.get("page"), 1)
        page_size = 20
        total = posts.count()
        start = (page - 1) * page_size
        end = start + page_size
        page_posts = posts[start:end]

        results = []
        for p in page_posts:
            results.append({
                "id": p.id,
                "author_name": p.author.nickname,
                "content": p.content,
                "created_at": p.created_at,
            })

        return api_response(data={
            "total": total,
            "page": page,
            "page_size": page_size,
            "results": results,
        })
