from datetime import datetime, UTC
from decimal import Decimal
import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase

from analytics_dashboard.views import analytics_dashboard_view, user_can_view_analytics


class UserCanViewAnalyticsTests(SimpleTestCase):
    def test_returns_false_for_unauthenticated_user(self):
        user = SimpleNamespace(is_authenticated=False)
        self.assertFalse(user_can_view_analytics(user))

    def test_returns_true_for_allowed_role_case_insensitive(self):
        user = SimpleNamespace(
            is_authenticated=True,
            profile=SimpleNamespace(
                role=SimpleNamespace(name="Admin")
            ),
        )
        self.assertTrue(user_can_view_analytics(user))

    def test_returns_false_for_disallowed_role(self):
        user = SimpleNamespace(
            is_authenticated=True,
            profile=SimpleNamespace(
                role=SimpleNamespace(name="customer")
            ),
        )
        self.assertFalse(user_can_view_analytics(user))

    def test_returns_false_when_profile_or_role_missing(self):
        user_without_profile = SimpleNamespace(is_authenticated=True)
        self.assertFalse(user_can_view_analytics(user_without_profile))

        user_without_role = SimpleNamespace(
            is_authenticated=True,
            profile=SimpleNamespace(role=None),
        )
        self.assertFalse(user_can_view_analytics(user_without_role))


class AnalyticsDashboardViewTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.allowed_user = SimpleNamespace(
            is_authenticated=True,
            profile=SimpleNamespace(
                role=SimpleNamespace(name="admin")
            ),
        )

    def make_request(self, params=None, user=None):
        request = self.factory.get("/analytics/", data=params or {})
        request.user = user or self.allowed_user
        return request

    def _setup_order_chain(
        self,
        mock_order,
        *,
        total_orders=6,
        paid_orders_count=4,
        total_revenue=Decimal("2400.00"),
        avg_check=Decimal("600.00"),
        orders_by_status=None,
        sales_by_day=None,
        latest_orders=None,
    ):
        if orders_by_status is None:
            orders_by_status = [
                {"status": "paid", "count": 4},
                {"status": None, "count": 2},
            ]

        if sales_by_day is None:
            sales_by_day = [
                {
                    "day": datetime(2026, 4, 20, 12, 0, tzinfo=UTC),
                    "orders_count": 2,
                    "revenue": Decimal("1200.00"),
                },
                {
                    "day": datetime(2026, 4, 21, 12, 0, tzinfo=UTC),
                    "orders_count": 2,
                    "revenue": Decimal("1200.00"),
                },
            ]

        if latest_orders is None:
            latest_orders = [
                SimpleNamespace(
                    id=1,
                    user=SimpleNamespace(username="boris"),
                    created_at=datetime(2026, 4, 21, 10, 30, tzinfo=UTC),
                    total_price=Decimal("1200.00"),
                    status="paid",
                ),
                SimpleNamespace(
                    id=2,
                    user=SimpleNamespace(username="anna"),
                    created_at=datetime(2026, 4, 22, 11, 0, tzinfo=UTC),
                    total_price=Decimal("800.00"),
                    status="pending",
                ),
            ]

        orders_qs = MagicMock(name="orders_qs")
        period_orders_qs = MagicMock(name="period_orders_qs")
        paid_orders_qs = MagicMock(name="paid_orders_qs")
        recent_paid_orders_qs = MagicMock(name="recent_paid_orders_qs")

        mock_order.objects.all.return_value = orders_qs

        def orders_filter_side_effect(*args, **kwargs):
            if kwargs == {"status": "paid"}:
                return paid_orders_qs
            if "created_at__gte" in kwargs:
                return period_orders_qs
            raise AssertionError(f"Unexpected Order.objects.filter call: {kwargs}")

        orders_qs.filter.side_effect = orders_filter_side_effect
        paid_orders_qs.filter.return_value = recent_paid_orders_qs

        period_orders_qs.count.return_value = total_orders
        recent_paid_orders_qs.count.return_value = paid_orders_count

        recent_paid_orders_qs.aggregate.side_effect = [
            {"total": total_revenue},
            {"avg": avg_check},
        ]

        status_values_qs = MagicMock(name="status_values_qs")
        status_annotated_qs = MagicMock(name="status_annotated_qs")
        period_orders_qs.values.return_value = status_values_qs
        status_values_qs.annotate.return_value = status_annotated_qs
        status_annotated_qs.order_by.return_value = orders_by_status

        sales_annotated_qs = MagicMock(name="sales_annotated_qs")
        sales_values_qs = MagicMock(name="sales_values_qs")
        sales_values_annotated_qs = MagicMock(name="sales_values_annotated_qs")

        recent_paid_orders_qs.annotate.return_value = sales_annotated_qs
        sales_annotated_qs.values.return_value = sales_values_qs
        sales_values_qs.annotate.return_value = sales_values_annotated_qs
        sales_values_annotated_qs.order_by.return_value = sales_by_day

        selected_qs = MagicMock(name="selected_qs")
        orders_qs.select_related.return_value = selected_qs
        selected_qs.order_by.return_value = latest_orders

    def _setup_order_item_chain(self, mock_order_item, *, top_books=None, popular_genres=None):
        if top_books is None:
            top_books = [
                {
                    "book__id": 1,
                    "book__title": "Мастер и Маргарита",
                    "sold_qty": 5,
                    "revenue": Decimal("2500.00"),
                },
                {
                    "book__id": 2,
                    "book__title": "Преступление и наказание",
                    "sold_qty": 3,
                    "revenue": Decimal("1500.00"),
                },
            ]

        if popular_genres is None:
            popular_genres = [
                {
                    "book__genres__name": "Роман",
                    "sold_qty": 6,
                    "revenue": Decimal("3000.00"),
                },
                {
                    "book__genres__name": "Классика",
                    "sold_qty": 4,
                    "revenue": Decimal("2000.00"),
                },
            ]

        top_filter_qs = MagicMock(name="top_filter_qs")
        top_values_qs = MagicMock(name="top_values_qs")
        top_annotate_qs = MagicMock(name="top_annotate_qs")
        top_order_qs = MagicMock(name="top_order_qs")

        genre_filter_qs = MagicMock(name="genre_filter_qs")
        genre_values_qs = MagicMock(name="genre_values_qs")
        genre_annotate_qs = MagicMock(name="genre_annotate_qs")
        genre_exclude_qs = MagicMock(name="genre_exclude_qs")
        genre_order_qs = MagicMock(name="genre_order_qs")

        mock_order_item.objects.filter.side_effect = [top_filter_qs, genre_filter_qs]

        top_filter_qs.values.return_value = top_values_qs
        top_values_qs.annotate.return_value = top_annotate_qs
        top_annotate_qs.order_by.return_value = top_order_qs
        top_order_qs.__getitem__.return_value = top_books

        genre_filter_qs.values.return_value = genre_values_qs
        genre_values_qs.annotate.return_value = genre_annotate_qs
        genre_annotate_qs.exclude.return_value = genre_exclude_qs
        genre_exclude_qs.order_by.return_value = genre_order_qs
        genre_order_qs.__getitem__.return_value = popular_genres

    @patch("analytics_dashboard.views.render")
    def test_redirects_to_login_for_unauthenticated_user(self, mock_render):
        request = self.make_request(user=SimpleNamespace(is_authenticated=False))
        response = analytics_dashboard_view(request)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)
        self.assertIn("next=/analytics/", response.url)
        mock_render.assert_not_called()

    @patch("analytics_dashboard.views.user_can_view_analytics", return_value=False)
    def test_returns_403_when_user_has_no_access(self, mock_access):
        request = self.make_request()
        response = analytics_dashboard_view(request)

        self.assertEqual(response.status_code, 403)
        self.assertIn("У вас нет доступа", response.content.decode("utf-8"))
        mock_access.assert_called_once_with(request.user)

    @patch("analytics_dashboard.views.render", return_value=HttpResponse("ok"))
    @patch("analytics_dashboard.views.OrderItem")
    @patch("analytics_dashboard.views.Order")
    @patch("analytics_dashboard.views.Book")
    @patch("analytics_dashboard.views.User")
    def test_uses_default_30_days_for_invalid_query_param(
        self,
        mock_user,
        mock_book,
        mock_order,
        mock_order_item,
        mock_render,
    ):
        mock_user.objects.count.return_value = 10
        mock_book.objects.count.return_value = 20

        self._setup_order_chain(mock_order)
        self._setup_order_item_chain(mock_order_item)

        request = self.make_request(params={"days": "abc"})
        response = analytics_dashboard_view(request)

        self.assertEqual(response.status_code, 200)

        args, kwargs = mock_render.call_args
        context = args[2]

        self.assertEqual(context["days"], 30)

    @patch("analytics_dashboard.views.render", return_value=HttpResponse("ok"))
    @patch("analytics_dashboard.views.OrderItem")
    @patch("analytics_dashboard.views.Order")
    @patch("analytics_dashboard.views.Book")
    @patch("analytics_dashboard.views.User")
    def test_builds_expected_context(
        self,
        mock_user,
        mock_book,
        mock_order,
        mock_order_item,
        mock_render,
    ):
        mock_user.objects.count.return_value = 14
        mock_book.objects.count.return_value = 33

        latest_orders = [
            SimpleNamespace(
                id=101,
                user=SimpleNamespace(username="boris"),
                created_at=datetime(2026, 4, 25, 13, 45, tzinfo=UTC),
                total_price=Decimal("1250.00"),
                status="paid",
            )
        ]

        self._setup_order_chain(
            mock_order,
            total_orders=8,
            paid_orders_count=5,
            total_revenue=Decimal("5400.00"),
            avg_check=Decimal("1080.00"),
            orders_by_status=[
                {"status": "paid", "count": 5},
                {"status": None, "count": 3},
            ],
            sales_by_day=[
                {
                    "day": datetime(2026, 4, 20, 12, 0, tzinfo=UTC),
                    "orders_count": 2,
                    "revenue": Decimal("1500.00"),
                },
                {
                    "day": datetime(2026, 4, 21, 12, 0, tzinfo=UTC),
                    "orders_count": 3,
                    "revenue": Decimal("3900.00"),
                },
            ],
            latest_orders=latest_orders,
        )

        self._setup_order_item_chain(
            mock_order_item,
            top_books=[
                {
                    "book__id": 1,
                    "book__title": "Герой нашего времени",
                    "sold_qty": 7,
                    "revenue": Decimal("3500.00"),
                }
            ],
            popular_genres=[
                {
                    "book__genres__name": "Классика",
                    "sold_qty": 9,
                    "revenue": Decimal("5400.00"),
                }
            ],
        )

        request = self.make_request(params={"days": "7"})
        response = analytics_dashboard_view(request)

        self.assertEqual(response.status_code, 200)

        args, kwargs = mock_render.call_args
        template_name = args[1]
        context = args[2]

        self.assertEqual(template_name, "analytics_dashboard/dashboard.html")
        self.assertEqual(context["days"], 7)
        self.assertEqual(context["total_users"], 14)
        self.assertEqual(context["total_books"], 33)
        self.assertEqual(context["total_orders"], 8)
        self.assertEqual(context["paid_orders_count"], 5)
        self.assertEqual(context["total_revenue"], Decimal("5400.00"))
        self.assertEqual(context["avg_check"], Decimal("1080.00"))
        self.assertEqual(len(context["top_books"]), 1)
        self.assertEqual(context["top_books"][0]["book__title"], "Герой нашего времени")
        self.assertEqual(len(context["popular_genres"]), 1)
        self.assertEqual(context["popular_genres"][0]["book__genres__name"], "Классика")
        self.assertEqual(context["latest_orders"], latest_orders)

        self.assertEqual(json.loads(context["sales_labels_json"]), ["20.04", "21.04"])
        self.assertEqual(json.loads(context["sales_orders_data_json"]), [2, 3])
        self.assertEqual(json.loads(context["sales_revenue_data_json"]), [1500.0, 3900.0])
        self.assertEqual(json.loads(context["status_labels_json"]), ["paid", "Без статуса"])
        self.assertEqual(json.loads(context["status_data_json"]), [5, 3])

    @patch("analytics_dashboard.views.render", return_value=HttpResponse("ok"))
    @patch("analytics_dashboard.views.OrderItem")
    @patch("analytics_dashboard.views.Order")
    @patch("analytics_dashboard.views.Book")
    @patch("analytics_dashboard.views.User")
    def test_falls_back_to_30_when_days_not_allowed(
        self,
        mock_user,
        mock_book,
        mock_order,
        mock_order_item,
        mock_render,
    ):
        mock_user.objects.count.return_value = 1
        mock_book.objects.count.return_value = 1

        self._setup_order_chain(mock_order)
        self._setup_order_item_chain(mock_order_item)

        request = self.make_request(params={"days": "999"})
        response = analytics_dashboard_view(request)

        self.assertEqual(response.status_code, 200)

        args, kwargs = mock_render.call_args
        context = args[2]
        self.assertEqual(context["days"], 30)