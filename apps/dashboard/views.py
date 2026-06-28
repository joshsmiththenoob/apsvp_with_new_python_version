from multiprocessing import context
from typing import Any

from django.shortcuts import render
from django.http import HttpResponse, HttpRequest
from django.views.generic.base import TemplateView

# Create your views here.
def hello_world(request: HttpRequest) -> HttpResponse:
    return HttpResponse("<h1>Hello, world!</h1>")


def get_menu_items() -> list[dict[str, str]]:
    return [
        {"name": "每日價量查詢", "url": "/chart/"},
        {"name": "監控清單", "url": "#"},
        {"name": "每日報表", "url": "#"},
    ]




class IndexView(TemplateView):
    template_name = "dashboard/index.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)

        context["title"] = "重要農產品價量平台 Mini"
        context["menu_items"] = get_menu_items()

        print(context)

        return context


class ChartPageView(TemplateView):
    template_name = "dashboard/chart_page.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)

        # Get query parameters from the request by using self.request.GET dictionary (It contains all the query strings).
        product_id = self.request.GET.get("product_id", "")
        start_date = self.request.GET.get("start_date", "2026-06-01")
        end_date = self.request.GET.get("end_date", "2026-06-25")


        # Setting context: title header informations 
        context["title"] = "重要農產品價量平台 Mini"
        context["page_title"] = "每日價量查詢"
        context["menu_items"] = get_menu_items()

        # Setting context: options data
        context["product_options"] = [
            {"id": "1", "name": "甘藍"},
            {"id": "2", "name": "結球白菜"},
            {"id": "3", "name": "青蔥"},
        ]


        context["selected_product_id"] = product_id
        context["start_date"] = start_date
        context["end_date"] = end_date

        # 先用假資料，不碰資料庫
        if product_id:
            context["rows"] = [
                {
                    "date": "2026-06-23",
                    "product_name": "甘藍",
                    "source_name": "台北一",
                    "avg_price": 35.2,
                    "volume": 1200,
                },
                {
                    "date": "2026-06-24",
                    "product_name": "甘藍",
                    "source_name": "台北一",
                    "avg_price": 36.1,
                    "volume": 1350,
                },
            ]
        else:
            context["rows"] = []
        
        print(context)

        return context