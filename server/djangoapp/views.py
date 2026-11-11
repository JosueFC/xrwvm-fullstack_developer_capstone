
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.contrib.auth.models import User
from django.contrib.auth import logout, login, authenticate
from django.contrib import messages
from datetime import datetime
import logging
import json
import requests

from django.views.decorators.csrf import csrf_exempt

from .populate import initiate
from .models import CarMake, CarModel
from .restapis import get_request, analyze_review_sentiments, post_review


# Get an instance of a logger
logger = logging.getLogger(__name__)


# Create a login_request view to handle sign in
@csrf_exempt
def login_user(request):
    if request.method != "POST":
        return JsonResponse({
            "status": 405,
            "message": "Method not allowed"
        }, status=405)

    try:
        data = json.loads(request.body)
        username = data['userName']
        password = data['password']

    except (json.JSONDecodeError, KeyError, TypeError):
        return JsonResponse({
            "status": 400,
            "message": "Invalid login data"
        }, status=400)

    user = authenticate(
        request,
        username=username,
        password=password
    )

    if user is not None:
        login(request, user)

        logger.info("User %s logged in successfully", username)

        return JsonResponse({
            "userName": username,
            "status": "Authenticated"
        })

    logger.warning("Failed login attempt for user %s", username)

    return JsonResponse({
        "userName": username,
        "status": "Unauthorized",
        "message": "Invalid username or password"
    }, status=401)


# Create a logout_request view to handle sign out
def logout_request(request):
    logout(request)

    return JsonResponse({
        "userName": ""
    })


# Create a registration view to handle sign up
@csrf_exempt
def registration(request):
    if request.method != "POST":
        return JsonResponse({
            "status": 405,
            "message": "Method not allowed"
        }, status=405)

    try:
        data = json.loads(request.body)

        username = data['userName']
        password = data['password']
        first_name = data['firstName']
        last_name = data['lastName']
        email = data['email']

    except (json.JSONDecodeError, KeyError, TypeError):
        return JsonResponse({
            "status": 400,
            "message": "Invalid registration data"
        }, status=400)

    if User.objects.filter(username=username).exists():
        return JsonResponse({
            "userName": username,
            "error": "Already Registered"
        })

    user = User.objects.create_user(
        username=username,
        first_name=first_name,
        last_name=last_name,
        password=password,
        email=email
    )

    login(request, user)

    logger.info(
        "New user %s registered and authenticated",
        username
    )

    return JsonResponse({
        "userName": username,
        "status": "Authenticated"
    })


# Get available car makes and models
def get_cars(request):
    count = CarMake.objects.count()

    if count == 0:
        initiate()

    car_models = CarModel.objects.select_related('car_make')

    cars = []

    for car_model in car_models:
        cars.append({
            "CarModel": car_model.name,
            "CarMake": car_model.car_make.name
        })

    return JsonResponse({
        "CarModels": cars
    })


# Get all dealerships or filter by state
def get_dealerships(request, state="All"):
    if state == "All":
        endpoint = "/fetchDealers"
    else:
        endpoint = "/fetchDealers/" + state

    dealerships = get_request(endpoint)

    if dealerships is None:
        logger.error("Unable to fetch dealerships")

        return JsonResponse({
            "status": 502,
            "message": "Unable to fetch dealerships",
            "dealers": []
        }, status=502)

    return JsonResponse({
        "status": 200,
        "dealers": dealerships
    })


# Get details for a specific dealer
def get_dealer_details(request, dealer_id):
    if not dealer_id:
        return JsonResponse({
            "status": 400,
            "message": "Bad Request"
        }, status=400)

    endpoint = "/fetchDealer/" + str(dealer_id)

    dealership = get_request(endpoint)

    if dealership is None:
        logger.error(
            "Unable to fetch dealer %s",
            dealer_id
        )

        return JsonResponse({
            "status": 502,
            "message": "Unable to fetch dealer details"
        }, status=502)

    return JsonResponse({
        "status": 200,
        "dealer": dealership
    })


# Get dealer reviews and analyze sentiment
def get_dealer_reviews(request, dealer_id):
    if not dealer_id:
        return JsonResponse({
            "status": 400,
            "message": "Bad Request"
        }, status=400)

    endpoint = "/fetchReviews/dealer/" + str(dealer_id)

    reviews = get_request(endpoint)

    if reviews is None:
        logger.error(
            "Unable to fetch reviews for dealer %s",
            dealer_id
        )

        return JsonResponse({
            "status": 502,
            "message": "Unable to fetch dealer reviews",
            "reviews": []
        }, status=502)

    for review_detail in reviews:
        review_text = review_detail.get('review', '')

        try:
            response = analyze_review_sentiments(review_text)

            if (
                isinstance(response, dict)
                and response.get('sentiment')
            ):
                review_detail['sentiment'] = response['sentiment']

            else:
                logger.warning(
                    "Sentiment analysis unavailable for dealer %s",
                    dealer_id
                )

                review_detail['sentiment'] = 'unknown'

        except Exception:
            logger.exception(
                "Sentiment analysis failed for dealer %s",
                dealer_id
            )

            review_detail['sentiment'] = 'unknown'

    return JsonResponse({
        "status": 200,
        "reviews": reviews
    })


# Submit a new dealership review
def add_review(request):

    # Diagnostic logging to investigate HTTP 403
    logger.warning(
        "Review submission authentication: "
        "user=%s, authenticated=%s, method=%s",
        request.user,
        request.user.is_authenticated,
        request.method
    )

    # Only allow POST requests
    if request.method != "POST":
        return JsonResponse({
            "status": 405,
            "message": "Method not allowed"
        }, status=405)

    # Check authentication
    if not request.user.is_authenticated:
        logger.warning(
            "Unauthorized review submission attempt"
        )

        return JsonResponse({
            "status": 403,
            "message": "Unauthorized. Please log in."
        }, status=403)

    # Parse review data
    try:
        data = json.loads(request.body)

        if not isinstance(data, dict):
            raise ValueError("Review data must be a JSON object")

    except (json.JSONDecodeError, ValueError, TypeError):
        logger.warning("Invalid review submission payload")

        return JsonResponse({
            "status": 400,
            "message": "Invalid review data"
        }, status=400)

    # Submit review to the backend service
    try:
        logger.info(
            "Submitting review for dealer %s",
            data.get('dealership')
        )

        response = post_review(data)

        logger.info(
            "Review backend response: %s",
            response
        )

        # Check the backend response
        if not isinstance(response, dict):
            raise ValueError(
                "Unexpected backend response"
            )

        # Detect explicitly reported errors
        backend_status = response.get("status")

        if (
            backend_status in (False, "error", "failed")
            or response.get("error")
        ):
            raise ValueError(
                "Backend reported a failed submission"
            )

        return JsonResponse({
            "status": 200,
            "message": "Review submitted",
            "result": response
        })

    except (ValueError, requests.RequestException):
        logger.exception(
            "Error submitting review"
        )

        return JsonResponse({
            "status": 502,
            "message": "Unable to submit review"
        }, status=502)

    except Exception:
        logger.exception(
            "Unexpected error submitting review"
        )

        return JsonResponse({
            "status": 500,
            "message": "Internal server error"
        }, status=500)
