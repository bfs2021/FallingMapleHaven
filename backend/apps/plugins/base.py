from abc import ABC, abstractmethod


class BasePlugin(ABC):
    plugin_type: str = ""
    display_name: str = ""
    description: str = ""
    icon: str = ""

    @abstractmethod
    def get_profile_data(self, user_id: int) -> dict:
        pass

    def get_routes(self) -> list:
        return []

    def get_admin_config(self) -> dict:
        return {}

    def get_summary(self, request_user_id: int) -> dict:
        """
        返回插件在 /plugins 独立页展示的全局摘要。
        默认行为等同于 get_profile_data。
        """
        return self.get_profile_data(request_user_id)

    def get_profile_card_data(self, viewer_id: int, owner_id: int):
        """
        访客看他人主页时，卡片展示的数据。
        viewer_id: 当前访问者用户ID
        owner_id: 主页主人用户ID
        返回 None 表示无数据不展示。
        默认行为：当 viewer_id == owner_id 时等同 get_profile_data，否则返回 None。
        """
        if viewer_id == owner_id:
            return self.get_profile_data(owner_id)
        return None
