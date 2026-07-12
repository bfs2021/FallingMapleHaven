from ..base import BasePlugin
from ..registry import register_plugin


@register_plugin
class QuizPlugin(BasePlugin):
    plugin_type = "quiz"
    display_name = "默契问答"
    description = "和朋友互相出题测试默契度"
    icon = "help-circle"

    def get_profile_data(self, user_id):
        from .models import QuizResult
        from django.db.models import Q
        results = QuizResult.objects.filter(
            Q(user_a_id=user_id) | Q(user_b_id=user_id)
        ).order_by("-updated_at")[:5]
        return {
            "type": self.plugin_type,
            "name": self.display_name,
            "icon": self.icon,
            "description": self.description,
            "data": {
                "friend_count": results.count(),
                "top_friends": [
                    {
                        "friend_id": r.user_a_id if r.user_b_id == user_id else r.user_b_id,
                        "match_score": float(r.match_score),
                    }
                    for r in results
                ],
            },
            "route": f"/profile/{user_id}/plugins/quiz",
        }

    def get_admin_config(self):
        return {
            "sidebar": [
                {
                    "path": "quizzes",
                    "name": "问答管理",
                    "icon": "❓",
                }
            ]
        }

    def get_summary(self, user_id):
        from .models import QuizResult
        from django.db.models import Q, Avg
        results = QuizResult.objects.filter(
            Q(user_a_id=user_id) | Q(user_b_id=user_id)
        )
        stats = results.aggregate(avg_score=Avg("match_score"))
        best = results.order_by("-match_score").first()

        def friend_of_result(r, uid):
            return r.user_b if r.user_a_id == uid else r.user_a

        return {
            "type": self.plugin_type,
            "name": self.display_name,
            "icon": self.icon,
            "description": self.description,
            "data": {
                "avg_match_rate": round(float(stats["avg_score"] or 0), 1),
                "best_friend_id": friend_of_result(best, user_id).id if best else None,
                "best_friend_name": friend_of_result(best, user_id).nickname if best else None,
                "best_match_rate": float(best.match_score) if best else 0,
                "total_friends_answered": results.count(),
            },
            "route": f"/profile/{user_id}/plugins/quiz",
        }

    def get_profile_card_data(self, viewer_id, owner_id):
        if viewer_id == owner_id:
            from .models import QuizResult
            from django.db.models import Q, Avg
            results = QuizResult.objects.filter(
                Q(user_a_id=owner_id) | Q(user_b_id=owner_id)
            )
            stats = results.aggregate(avg_score=Avg("match_score"))
            return {
                "type": self.plugin_type,
                "name": self.display_name,
                "icon": self.icon,
                "description": self.description,
                "data": {
                    "avg_match_rate": round(float(stats["avg_score"] or 0), 1),
                    "friend_count": results.count(),
                },
                "route": f"/profile/{owner_id}/plugins/quiz",
            }
        from .models import QuizResult
        from django.db.models import Q
        result = QuizResult.objects.filter(
            Q(user_a_id=viewer_id, user_b_id=owner_id) |
            Q(user_a_id=owner_id, user_b_id=viewer_id)
        ).first()
        if not result:
            return None
        return {
            "type": self.plugin_type,
            "name": self.display_name,
            "icon": self.icon,
            "description": self.description,
            "data": {
                "match_score": float(result.match_score),
                "total_questions": result.total_questions,
                "correct_count": result.correct_count,
            },
            "route": f"/profile/{owner_id}/plugins/quiz",
        }
