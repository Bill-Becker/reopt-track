import os
from pathlib import Path
import json
import pandas as pd
from datetime import datetime
import requests
from django.conf import settings
from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import RunMeta
from .serializer import RunMetaSerializer

# Create your views here.

def dashboard(request):
    # Generate the data for the chart
    chart_data = generate_chart_data()

    # Pass the chart data to the template
    context = {
        'chart_data': json.dumps(chart_data)
    }

    return render(request, 'reopt/dashboard.html', context)

@api_view(["GET"])
def getData(request):
    # Serialize the data from the database into dict/JSON
    # The run_data is included in the run_meta objects, so we just have to serialize run_meta
    if request.query_params.get("run_meta_id"):
        run_meta = RunMeta.objects.get(id=request.query_params.get("run_meta_id"))
        run_meta_serialized = RunMetaSerializer(run_meta)
    else:
        all_meta = RunMeta.objects.all()
        run_meta_serialized = RunMetaSerializer(all_meta, many=True)
    
    return Response(run_meta_serialized.data)


@api_view(["POST"])
def postRun(request):
    # De-serialize the data from the request into python/model objects
    # The DRF Serializer validates the data before saving it to the database and handles errors
    run_meta_serializer = RunMetaSerializer(data=request.data)
    if run_meta_serializer.is_valid():
        run_meta_serializer.save()
        return Response({"run_meta_id": run_meta_serializer.data["id"]}, status=201)
    return Response(run_meta_serializer.errors, status=400)

@api_view(["PATCH"])
def updateRun(request):
    try:
        run_meta = RunMeta.objects.get(id=request.query_params.get("run_meta_id"))
    except RunMeta.DoesNotExist:
        return Response({"error": "RunMeta not found"}, status=404)

    run_meta_serializer = RunMetaSerializer(run_meta, data=request.data, partial=True)
    if run_meta_serializer.is_valid():
        run_meta_serializer.save()
        return Response(run_meta_serializer.data, status=200)
    return Response(run_meta_serializer.errors, status=400)

def generate_chart_data():
    # API users up through FY24, stored in a file
    api_users_file_path = os.path.join(settings.BASE_DIR, 'reopt', 'data', 'api_users_thru_FY24.json')
    with open(api_users_file_path, 'r') as file:
        older_api_users = json.load(file)
    older_api_users_df = pd.DataFrame(older_api_users["data"])

    # Call api.data.gov API for latest API users FY25 through today
    api_users_api_response = get_api_gov_data(api_or_jl="api", users_or_runs="users", start_date="2024-10-01", end_date=datetime.today().strftime('%Y-%m-%d'), interval="month")
    latest_users_df = pd.DataFrame(api_users_api_response["data"])

    # Append both sets of API users to get full list of users from beginning through today
    api_users = pd.concat([older_api_users_df, latest_users_df], ignore_index=True)

    # Convert the "created_at" column to datetime and filter to just users who signed up from 2017 through today
    api_users['created_at'] = pd.to_datetime(api_users['created_at'])
    api_users = api_users[api_users['created_at'] > '2017-01-01']

    # Group data by quarters and calculate cumulative users
    api_users.set_index('created_at', inplace=True)
    api_users_quarterly = api_users.resample('QE').size().cumsum()

    # Call api.data.gov API for REopt.jl user data
    reoptjl_users_api_response = get_api_gov_data(api_or_jl="jl", users_or_runs="users", start_date="2022-10-01", end_date=datetime.today().strftime('%Y-%m-%d'), interval="month")
    reoptjl_users = pd.DataFrame(reoptjl_users_api_response["data"])
    # Convert the "Signed Up (UTC)" column to datetime
    reoptjl_users['created_at'] = pd.to_datetime(reoptjl_users['created_at'])

    # Filter users who signed up from 2017 through 2024
    reoptjl_users = reoptjl_users[reoptjl_users['created_at'] >= '2017-01-01']
    # Cumulate reoptjl_users with created_at before 2022-10-01 into Q1 2022
    reoptjl_users_before_fy23 = reoptjl_users[reoptjl_users['created_at'] < '2022-10-01']
    reoptjl_users_before_fy23_count = len(reoptjl_users_before_fy23)
    
    # TODO make these NREL's fiscal year quarters instead of calendar year quarters
    
    # Group data by quarters and calculate cumulative users
    reoptjl_users.set_index('created_at', inplace=True)
    reoptjl_users_quarterly = reoptjl_users.resample('QE').size().cumsum()
    reoptjl_users_quarterly.loc[reoptjl_users_quarterly.index < '2022-09-30'] = 0
    reoptjl_users_quarterly.loc['2022-09-30'] = reoptjl_users_before_fy23_count

    # Reindex reoptjl_users_quarterly to match api_users_quarterly
    reoptjl_users_quarterly = reoptjl_users_quarterly.reindex(api_users_quarterly.index, fill_value=0)

    # Prepare data for Chart.js
    chart_data = {
        'labels': [f'Q{((date.month-1)//3)+1} {date.year}' for date in api_users_quarterly.index],  # Format as 'Q1 2022', 'Q2 2022', etc.
        'datasets': [
            {
                'label': 'API Users',
                'data': api_users_quarterly.tolist(),
                'backgroundColor': 'rgba(75, 192, 192, 0.2)',
                'borderColor': 'rgba(75, 192, 192, 1)',
                'borderWidth': 1
            },
            {
                'label': 'REopt.jl Users',
                'data': reoptjl_users_quarterly.tolist(),
                'backgroundColor': 'rgba(153, 102, 255, 0.2)',
                'borderColor': 'rgba(153, 102, 255, 1)',
                'borderWidth': 1
            }
        ]
    }

    return chart_data


def get_api_gov_data(*, api_or_jl, users_or_runs, start_date, end_date=datetime.today().strftime('%Y-%m-%d'), interval="month"):
    # Update default query for API vs REopt.jl -> PVWatts and Users vs Runs data
    if api_or_jl == "api":
        if users_or_runs == "users":
            query = '%7B"condition"%3A"AND"%2C"rules"%3A%5B%7B"id"%3A"request_path"%2C"field"%3A"request_path"%2C"type"%3A"string"%2C"input"%3A"text"%2C"operator"%3A"contains"%2C"value"%3A"reopt"%7D%5D%2C"valid"%3Atrue%7D'
            base_url = "https://api.data.gov/admin/stats/users.json?"
        elif users_or_runs == "runs":
            prefix = '3%2Fdeveloper.nrel.gov%2Fapi%2Freopt%2F'
            query = '%7B"condition"%3A"AND"%2C"rules"%3A%5B%7B"id"%3A"request_path"%2C"field"%3A"request_path"%2C"type"%3A"string"%2C"input"%3A"text"%2C"operator"%3A"contains"%2C"value"%3A"%2Fjob"%7D%2C%7B"id"%3A"request_method"%2C"field"%3A"request_method"%2C"type"%3A"string"%2C"input"%3A"select"%2C"operator"%3A"equal"%2C"value"%3A"post"%7D%5D%2C"valid"%3Atrue%7D'
            base_url = "https://api.data.gov/api-umbrella/v1/analytics/drilldown.json?prefix=" + prefix 
        else:
            print("Error: Invalid users_or_runs. Please specify either 'users' or 'runs'.")
    elif api_or_jl == "jl":
        if users_or_runs == "users":
            query = '%7B"condition"%3A"AND"%2C"rules"%3A%5B%7B"id"%3A"request_path"%2C"field"%3A"request_path"%2C"type"%3A"string"%2C"input"%3A"text"%2C"operator"%3A"contains"%2C"value"%3A"pvwatts"%7D%2C%7B"id"%3A"request_user_agent"%2C"field"%3A"request_user_agent"%2C"type"%3A"string"%2C"input"%3A"text"%2C"operator"%3A"contains"%2C"value"%3A".jl"%7D%5D%2C"valid"%3Atrue%7D'
            base_url = "https://api.data.gov/admin/stats/users.json?"
        elif users_or_runs == "runs":
            prefix = '3%2Fdeveloper.nrel.gov%2Fapi%2Fpvwatts%2F'
            # query = '%7B"condition"%3A"AND"%2C"rules"%3A%5B%7B"id"%3A"request_user_agent"%2C"field"%3A"request_user_agent"%2C"type"%3A"string"%2C"input"%3A"text"%2C"operator"%3A"contains"%2C"value"%3A".jl"%7D%5D%2C"valid"%3Atrue%7D'
            # Do NOT include the REopt_API user reopt-api-wind-toolkit.api_keys@nrel.gov and the REopt.jl GitHub Actions tests user laws.nick@nrel.gov
            query = '%7B"condition"%3A"AND"%2C"rules"%3A%5B%7B"id"%3A"request_user_agent"%2C"field"%3A"request_user_agent"%2C"type"%3A"string"%2C"input"%3A"text"%2C"operator"%3A"contains"%2C"value"%3A".jl"%7D%2C%7B"id"%3A"user_email"%2C"field"%3A"user_email"%2C"type"%3A"string"%2C"input"%3A"text"%2C"operator"%3A"not_contains"%2C"value"%3A"reopt-api-wind-toolkit.api_keys%40nrel.gov"%7D%2C%7B"id"%3A"user_email"%2C"field"%3A"user_email"%2C"type"%3A"string"%2C"input"%3A"text"%2C"operator"%3A"not_contains"%2C"value"%3A"laws.nick%40gmail.com"%7D%5D%2C"valid"%3Atrue%7D'
            base_url = "https://api.data.gov/api-umbrella/v1/analytics/drilldown.json?prefix=" + prefix 
        else:
            print("Error: Invalid users_or_runs. Please specify either 'users' or 'runs'.")       
    else:
        print("Error: Invalid api_or_jl. Please specify either 'api' or 'jl'.")

    # Expects these ENV variables to be set
    headers = {
        "X-Admin-Auth-Token": os.environ.get('ADMIN_AUTH_TOKEN'),
        "X-Api-Key": os.environ.get('API_KEY')
    }

    print("headers = " + str(headers))

    # Note: the base URL already contains a "?" character and if applicable, the prefix, so we need and "&" character for the first parameter "query" here
    jobs_url = base_url + \
        "&query=" + query + \
            "&start_at=" + start_date + \
                "&end_at=" + end_date + \
                    "&interval=" + interval
    
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