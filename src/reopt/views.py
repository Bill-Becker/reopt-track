import json
import os
from datetime import datetime

import folium
import pandas as pd
import requests
from django.conf import settings
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.templatetags.static import static
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import RunData
from .models import RunMeta
from .serializer import RunMetaSerializer

# Create your views here.


def dashboard(request):
    data_dir = os.path.join(settings.BASE_DIR, 'reopt', 'data')
    user_chart_data_path = os.path.join(data_dir, 'user_chart_data.json')
    run_chart_data_path = os.path.join(data_dir, 'run_chart_data.json')
    track_data_path = os.path.join(data_dir, 'track_data.json')

    # Check if any of the data files do not exist
    if not (os.path.exists(user_chart_data_path) and os.path.exists(run_chart_data_path) and os.path.exists(track_data_path)):
        # Call the update_chart_data view to generate the data files
        update_chart_data(request)
        # Redirect back to the dashboard
        return redirect('reopt_dashboard')

    with open(os.path.join(data_dir, 'user_chart_data.json'), 'r') as f:
        user_chart_data = json.load(f)

    with open(os.path.join(data_dir, 'run_chart_data.json'), 'r') as f:
        run_chart_data = json.load(f)

    with open(os.path.join(data_dir, 'track_data.json'), 'r') as f:
        track_data = json.load(f)

    user_locations_map_path = get_user_locations_map()
    run_locations_map_path = get_run_locations_map()

    context = {
        "user_chart_data": json.dumps(user_chart_data),
        "run_chart_data": json.dumps(run_chart_data),
        "track_data": json.dumps(track_data),
        "user_locations_map_path": user_locations_map_path,
        "run_locations_map_path": run_locations_map_path,
    }

    return render(request, "reopt/dashboard.html", context)


def update_chart_data(request):
    user_chart_data = get_user_chart_data_from_api_gov()
    run_chart_data = get_run_chart_data_from_api_gov()
    track_data = get_run_counts_from_track_db()

    data_dir = os.path.join(settings.BASE_DIR, 'reopt', 'data')
    os.makedirs(data_dir, exist_ok=True)

    with open(os.path.join(data_dir, 'user_chart_data.json'), 'w') as f:
        json.dump(user_chart_data, f)

    with open(os.path.join(data_dir, 'run_chart_data.json'), 'w') as f:
        json.dump(run_chart_data, f)

    with open(os.path.join(data_dir, 'track_data.json'), 'w') as f:
        json.dump(track_data, f)

    return JsonResponse({'status': 'success'})


@api_view(["GET"])
def getData(request):
    # Serialize the data from the database into dict/JSON
    # The run_data is included in the run_meta objects, so we just have to serialize run_meta
    if request.query_params.get("run_meta_id"):
        run_meta = RunMeta.objects.get(
            id=request.query_params.get("run_meta_id")
        )
        run_meta_serialized = RunMetaSerializer(run_meta)
    else:
        all_meta = RunMeta.objects.all()
        run_meta_serialized = RunMetaSerializer(all_meta, many=True)

    return Response(run_meta_serialized.data)


@api_view(["POST"])
def postRun(request):
    # De-serialize the data from the request into python/model objects
    # The DRF Serializer validates the data before saving it to the database and handles errors
    user_data = get_user_location_from_request(request)
    request.data["user_ip_address"] = user_data.get("query")
    request.data["user_country"] = user_data.get("country")
    request.data["user_region"] = user_data.get("regionName")
    request.data["user_city"] = user_data.get("city")
    request.data["user_latitude"] = user_data.get("lat")
    request.data["user_longitude"] = user_data.get("lon")
    run_meta_serializer = RunMetaSerializer(data=request.data)
    if run_meta_serializer.is_valid():
        run_meta_serializer.save()
        return Response(
            {"run_meta_id": run_meta_serializer.data["id"]}, status=201
        )
    return Response(run_meta_serializer.errors, status=400)


@api_view(["PATCH"])
def updateRun(request):
    try:
        run_meta = RunMeta.objects.get(
            id=request.query_params.get("run_meta_id")
        )
    except RunMeta.DoesNotExist:
        return Response({"error": "RunMeta not found"}, status=404)

    run_meta_serializer = RunMetaSerializer(
        run_meta, data=request.data, partial=True
    )
    if run_meta_serializer.is_valid():
        run_meta_serializer.save()
        return Response(run_meta_serializer.data, status=200)
    return Response(run_meta_serializer.errors, status=400)


def get_run_counts_from_track_db():
    # Query the RunMeta model for all entries
    run_meta_entries = RunMeta.objects.all()

    # Create a DataFrame from the query set
    data = {
        "created": [entry.created for entry in run_meta_entries],
        "direct_reoptjl": [entry.direct_reoptjl for entry in run_meta_entries],
        "direct_api_run": [entry.direct_api_run for entry in run_meta_entries],
        "webtool_run": [entry.webtool_run for entry in run_meta_entries],
    }
    df = pd.DataFrame(data)

    # Convert the "created" column to datetime
    df["created"] = pd.to_datetime(df["created"])

    # Group data by calendar year quarter and sum the counts
    df.set_index("created", inplace=True)
    quarterly_counts = df.resample("QE").sum()

    # quarterly_counts.to_dict(orient="index")

    # Prepare track_data
    track_data = {
        "labels": [
            f"Q{((date.month - 10) // 3) % 4 + 1} {date.year + 1 if date.month >= 10 else date.year}"
            for date in quarterly_counts.index
        ],  # Format as 'Q1 2022', 'Q2 2022', etc.
        "datasets": [
            {
                "label": "REopt.jl",
                "data": quarterly_counts["direct_reoptjl"].tolist(),
                "backgroundColor": "rgba(153, 102, 255, 0.2)",
                "borderColor": "rgba(153, 102, 255, 1)",
                "borderWidth": 1,
            },
            {
                "label": "API",
                "data": quarterly_counts["direct_api_run"].tolist(),
                "backgroundColor": "rgba(75, 192, 192, 0.2)",
                "borderColor": "rgba(75, 192, 192, 1)",
                "borderWidth": 1,
            },
            {
                "label": "Webtool",
                "data": quarterly_counts["webtool_run"].tolist(),
                "backgroundColor": "rgba(255, 99, 132, 0.2)",
                "borderColor": "rgba(255, 99, 132, 1)",
                "borderWidth": 1,
            },
        ],
    }

    return track_data


def get_user_location(ip_address):
    url = f"http://ip-api.com/json/{ip_address}"
    response = requests.get(url)
    location_data = response.json()
    return location_data


def get_public_ip():
    response = requests.get("https://api.ipify.org?format=json", verify=False)
    ip_data = response.json()
    return ip_data["ip"]


def get_user_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")

    # If the IP is a private IP, get the public IP
    if (
        ip.startswith("192.168.")
        or ip.startswith("10.")
        or ip.startswith("172.16.")
        or ip == "127.0.0.1"
        or ip.startswith("172.18.")
    ):
        ip = get_public_ip()

    return ip


def get_user_location_from_request(request):
    ip = get_user_ip(request)
    location_data = get_user_location(ip)
    return location_data


def get_user_locations_map():
    # Retrieve all user cities from the RunMeta model
    run_meta_entries = RunMeta.objects.all()
    user_location = [
        (
            entry.user_city,
            entry.user_region,
            entry.user_country,
            entry.user_latitude,
            entry.user_longitude,
        )
        for entry in run_meta_entries
    ]

    # Create a map centered at a default location
    user_map = folium.Map(location=[0, 0], zoom_start=2)

    # Add markers for each city
    for city, state, country, lat, lon in user_location:
        if (lat is not None) and (lon is not None):
            folium.Marker(
                location=[float(lat), float(lon)],
                popup=f"{city}, {state}, {country}",
            ).add_to(user_map)

    # # Save the map to an HTML file in the static directory
    map_file_path = os.path.join(
        settings.STATICFILES_DIRS[1], "user_location_map.html"
    )
    user_map.save(map_file_path)

    # return map_file_path
    return static("user_location_map.html")


def get_run_locations_map():
    # Retrieve all user cities from the RunMeta model
    run_data_entries = RunData.objects.all()
    user_location = [
        (entry.latitude, entry.longitude) for entry in run_data_entries
    ]

    # Create a map centered at a default location
    run_map = folium.Map(location=[0, 0], zoom_start=2)

    # Add markers for each city
    for lat, lon in user_location:
        if lat and lon:
            folium.Marker(
                location=[float(lat), float(lon)], popup=f"{lat}, {lon}"
            ).add_to(run_map)

    # # Save the map to an HTML file in the static directory
    map_file_path = os.path.join(
        settings.STATICFILES_DIRS[1], "run_location_map.html"
    )
    run_map.save(map_file_path)

    # return map_file_path
    return static("run_location_map.html")


def get_user_chart_data_from_api_gov():
    # API users up through FY24, stored in a file
    api_users_file_path = os.path.join(
        settings.BASE_DIR, "reopt", "data", "api_users_thru_FY24.json"
    )
    with open(api_users_file_path, "r") as file:
        older_api_users = json.load(file)
    older_api_users_df = pd.DataFrame(older_api_users["data"])

    # Call api.data.gov API for latest API users FY25 through today
    api_users_api_response = get_api_gov_data(
        api_or_jl="api",
        users_or_runs="users",
        start_date="2024-10-01",
        end_date=datetime.today().strftime("%Y-%m-%d"),
        interval="month",
    )
    latest_users_df = pd.DataFrame(api_users_api_response["data"])

    # Append both sets of API users to get full list of users from beginning through today
    api_users = pd.concat(
        [older_api_users_df, latest_users_df], ignore_index=True
    )

    # Convert the "created_at" column to datetime and filter to just users who signed up from 2017 through today
    api_users["created_at"] = pd.to_datetime(api_users["created_at"])
    api_users = api_users[api_users["created_at"] > "2017-10-01"]

    # Group data by quarters and calculate cumulative users
    api_users.set_index("created_at", inplace=True)
    api_users_quarterly = api_users.resample("QE").size().cumsum()

    # Call api.data.gov API for REopt.jl user data
    reoptjl_users_api_response = get_api_gov_data(
        api_or_jl="jl",
        users_or_runs="users",
        start_date="2022-10-01",
        end_date=datetime.today().strftime("%Y-%m-%d"),
        interval="month",
    )
    reoptjl_users = pd.DataFrame(reoptjl_users_api_response["data"])
    # Convert the "Signed Up (UTC)" column to datetime
    reoptjl_users["created_at"] = pd.to_datetime(reoptjl_users["created_at"])

    # Filter users who signed up from 2017 through 2024
    reoptjl_users = reoptjl_users[reoptjl_users["created_at"] >= "2017-10-01"]
    # Cumulate reoptjl_users with created_at before 2022-10-01 into Q1 2022
    reoptjl_users_before_fy23 = reoptjl_users[
        reoptjl_users["created_at"] < "2022-10-01"
    ]
    reoptjl_users_before_fy23_count = len(reoptjl_users_before_fy23)

    # Group data by quarters and calculate cumulative users
    reoptjl_users.set_index("created_at", inplace=True)
    reoptjl_users_quarterly = reoptjl_users.resample("QE").size().cumsum()
    reoptjl_users_quarterly.loc[
        reoptjl_users_quarterly.index < "2022-09-30"
    ] = 0
    reoptjl_users_quarterly.loc["2022-09-30"] = reoptjl_users_before_fy23_count

    # Reindex reoptjl_users_quarterly to match api_users_quarterly
    reoptjl_users_quarterly = reoptjl_users_quarterly.reindex(
        api_users_quarterly.index, fill_value=0
    )

    # Prepare data for Chart.js
    chart_data = {
        "labels": [
            f"Q{((date.month - 10) // 3) % 4 + 1} {date.year + 1 if date.month >= 10 else date.year}"
            for date in api_users_quarterly.index
        ],  # Format as 'Q1 2022', 'Q2 2022', etc.
        "datasets": [
            {
                "label": "API Users",
                "data": api_users_quarterly.tolist(),
                "backgroundColor": "rgba(75, 192, 192, 0.2)",
                "borderColor": "rgba(75, 192, 192, 1)",
                "borderWidth": 1,
            },
            {
                "label": "REopt.jl Users",
                "data": reoptjl_users_quarterly.tolist(),
                "backgroundColor": "rgba(153, 102, 255, 0.2)",
                "borderColor": "rgba(153, 102, 255, 1)",
                "borderWidth": 1,
            },
        ],
    }

    return chart_data


def get_run_chart_data_from_api_gov():
    # API runs up through FY24, stored in a file
    api_runs_file_path = os.path.join(
        settings.BASE_DIR, "reopt", "data", "api_run_data_thru_FY24.json"
    )
    with open(api_runs_file_path, "r") as file:
        older_api_runs_json = json.load(file)

    # Call api.data.gov API for latest API runs FY25 through today
    api_runs_api_response = get_api_gov_data(
        api_or_jl="api",
        users_or_runs="runs",
        start_date="2024-10-01",
        end_date=datetime.today().strftime("%Y-%m-%d"),
        interval="month",
    )

    # Append both sets of API runs to get full list of runs from beginning through today
    all_runs = (
        older_api_runs_json["hits_over_time"]["rows"]
        + api_runs_api_response["hits_over_time"]["rows"]
    )

    runs_arr = []
    run_date_range = []
    for c in range(len(all_runs)):
        run_c = all_runs[c]["c"]
        runs_arr.append(sum([run_c[v]["v"] for v in range(1, len(run_c))]))
        run_date_range.append(run_c[0]["f"])

    # Convert elements of run_date_range to datetime objects
    run_date_range_dt = [
        datetime.strptime(date_range.split(" - ")[0], "%b %d, %Y")
        for date_range in run_date_range
    ]

    # Create a pandas series with run_date_range_dt as the index and runs_arr as the data
    api_runs = pd.Series(data=runs_arr, index=run_date_range_dt)

    # Group data by quarters and calculate cumulative runs
    api_runs_quarterly = api_runs.resample("QE").sum().cumsum()

    # Call api.data.gov API for REopt.jl run data - note we are not storing and loading REopt.jl run data locally
    reoptjl_runs_api_response = get_api_gov_data(
        api_or_jl="jl",
        users_or_runs="runs",
        start_date="2022-10-01",
        end_date=datetime.today().strftime("%Y-%m-%d"),
        interval="month",
    )

    runs_arr = []
    run_date_range = []
    for c in range(len(reoptjl_runs_api_response["hits_over_time"]["rows"])):
        run_c = reoptjl_runs_api_response["hits_over_time"]["rows"][c]["c"]
        runs_arr.append(sum([run_c[v]["v"] for v in range(1, len(run_c))]))
        run_date_range.append(run_c[0]["f"])

    # Convert elements of run_date_range to datetime objects
    run_date_range_dt = [
        datetime.strptime(date_range.split(" - ")[0], "%b %d, %Y")
        for date_range in run_date_range
    ]

    # Create a pandas series with run_date_range_dt as the index and runs_arr as the data
    reoptjl_runs = pd.Series(data=runs_arr, index=run_date_range_dt)

    # Group data by quarters and calculate cumulative runs
    reoptjl_runs_quarterly = reoptjl_runs.resample("QE").sum().cumsum()

    # Reindex reoptjl_runs_quarterly to match api_runs_quarterly
    reoptjl_runs_quarterly = reoptjl_runs_quarterly.reindex(
        api_runs_quarterly.index, fill_value=0
    )

    # Prepare data for Chart.js
    chart_data = {
        "labels": [
            f"Q{((date.month - 10) // 3) % 4 + 1} {date.year + 1 if date.month >= 10 else date.year}"
            for date in api_runs_quarterly.index
        ],  # Format as 'Q1 2022', 'Q2 2022', etc.
        "datasets": [
            {
                "label": "API Runs",
                "data": api_runs_quarterly.tolist(),
                "backgroundColor": "rgba(75, 192, 192, 0.2)",
                "borderColor": "rgba(75, 192, 192, 1)",
                "borderWidth": 1,
            },
            {
                "label": "REopt.jl Runs",
                "data": reoptjl_runs_quarterly.tolist(),
                "backgroundColor": "rgba(153, 102, 255, 0.2)",
                "borderColor": "rgba(153, 102, 255, 1)",
                "borderWidth": 1,
            },
        ],
    }

    return chart_data


def get_api_gov_data(
    *,
    api_or_jl,
    users_or_runs,
    start_date,
    end_date=datetime.today().strftime("%Y-%m-%d"),
    interval="month",
):
    # Update default query for API vs REopt.jl -> PVWatts and Users vs Runs data
    if api_or_jl == "api":
        if users_or_runs == "users":
            query = '%7B"condition"%3A"AND"%2C"rules"%3A%5B%7B"id"%3A"request_path"%2C"field"%3A"request_path"%2C"type"%3A"string"%2C"input"%3A"text"%2C"operator"%3A"contains"%2C"value"%3A"reopt"%7D%5D%2C"valid"%3Atrue%7D'
            base_url = "https://api.data.gov/admin/stats/users.json?"
        elif users_or_runs == "runs":
            prefix = "3%2Fdeveloper.nrel.gov%2Fapi%2Freopt%2F"
            query = '%7B"condition"%3A"AND"%2C"rules"%3A%5B%7B"id"%3A"request_path"%2C"field"%3A"request_path"%2C"type"%3A"string"%2C"input"%3A"text"%2C"operator"%3A"contains"%2C"value"%3A"%2Fjob"%7D%2C%7B"id"%3A"request_method"%2C"field"%3A"request_method"%2C"type"%3A"string"%2C"input"%3A"select"%2C"operator"%3A"equal"%2C"value"%3A"post"%7D%5D%2C"valid"%3Atrue%7D'
            base_url = (
                "https://api.data.gov/api-umbrella/v1/analytics/drilldown.json?prefix="
                + prefix
            )
        else:
            print(
                "Error: Invalid users_or_runs. Please specify either 'users' or 'runs'."
            )
    elif api_or_jl == "jl":
        if users_or_runs == "users":
            query = '%7B"condition"%3A"AND"%2C"rules"%3A%5B%7B"id"%3A"request_path"%2C"field"%3A"request_path"%2C"type"%3A"string"%2C"input"%3A"text"%2C"operator"%3A"contains"%2C"value"%3A"pvwatts"%7D%2C%7B"id"%3A"request_user_agent"%2C"field"%3A"request_user_agent"%2C"type"%3A"string"%2C"input"%3A"text"%2C"operator"%3A"contains"%2C"value"%3A".jl"%7D%5D%2C"valid"%3Atrue%7D'
            base_url = "https://api.data.gov/admin/stats/users.json?"
        elif users_or_runs == "runs":
            prefix = "3%2Fdeveloper.nrel.gov%2Fapi%2Fpvwatts%2F"
            # query = '%7B"condition"%3A"AND"%2C"rules"%3A%5B%7B"id"%3A"request_user_agent"%2C"field"%3A"request_user_agent"%2C"type"%3A"string"%2C"input"%3A"text"%2C"operator"%3A"contains"%2C"value"%3A".jl"%7D%5D%2C"valid"%3Atrue%7D'
            # Do NOT include the REopt_API user reopt-api-wind-toolkit.api_keys@nrel.gov and the REopt.jl GitHub Actions tests user laws.nick@nrel.gov
            query = '%7B"condition"%3A"AND"%2C"rules"%3A%5B%7B"id"%3A"request_user_agent"%2C"field"%3A"request_user_agent"%2C"type"%3A"string"%2C"input"%3A"text"%2C"operator"%3A"contains"%2C"value"%3A".jl"%7D%2C%7B"id"%3A"user_email"%2C"field"%3A"user_email"%2C"type"%3A"string"%2C"input"%3A"text"%2C"operator"%3A"not_contains"%2C"value"%3A"reopt-api-wind-toolkit.api_keys%40nrel.gov"%7D%2C%7B"id"%3A"user_email"%2C"field"%3A"user_email"%2C"type"%3A"string"%2C"input"%3A"text"%2C"operator"%3A"not_contains"%2C"value"%3A"laws.nick%40gmail.com"%7D%5D%2C"valid"%3Atrue%7D'
            base_url = (
                "https://api.data.gov/api-umbrella/v1/analytics/drilldown.json?prefix="
                + prefix
            )
        else:
            print(
                "Error: Invalid users_or_runs. Please specify either 'users' or 'runs'."
            )
    else:
        print("Error: Invalid api_or_jl. Please specify either 'api' or 'jl'.")

    # Expects these ENV variables to be set
    headers = {
        "X-Admin-Auth-Token": os.environ.get("ADMIN_AUTH_TOKEN"),
        "X-Api-Key": os.environ.get("API_KEY"),
    }

    print("headers = " + str(headers))

    # Note: the base URL already contains a "?" character and if applicable, the prefix, so we need and "&" character for the first parameter "query" here
    jobs_url = (
        base_url
        + "&query="
        + query
        + "&start_at="
        + start_date
        + "&end_at="
        + end_date
        + "&interval="
        + interval
    )

    r = requests.get(jobs_url, headers=headers)

    if r.status_code == 200:
        try:
            response = r.json()
            print("API response successfully parsed.")
        except json.JSONDecodeError:
            print("Error: Failed to parse JSON response.")
    else:
        print(f"Error: Received status code {r.status_code}")
        print(r.text)

    return response
