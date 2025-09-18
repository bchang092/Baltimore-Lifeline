from django.shortcuts import render

# Create your views here.
def resources_map(request):
    resources = [
        {
            "id": 1,
            "name": "Free Clinic",
            "lat": 39.2904,
            "lng": -76.6122,
            "category": "Health",
            "phone_number": "123-456-7890",
            "address": "123 Main St, Baltimore, MD",
            "description": "Provides free primary care services for uninsured residents.",
        },
        {
            "id": 1,
            "name": "Free Clinic_2",
            "lat": 39.324265,
            "lng": -76.596524,
            "category": "Health",
            "phone_number": "123-456-7890",
            "address": "2800 Kirk Avenue, Baltimore, MD",
            "description": "Provides free primary care services for uninsured residents.",
        },
        {
            "id": 2,
            "name": "Food Pantry",
            "lat": 39.3045,
            "lng": -76.6170,
            "category": "Food",
            "phone_number": "123-456-7890",
            "address": "456 Pine Ave, Baltimore, MD",
            "description": "Provides free primary care services for uninsured residents.",
        },
        {
            "id": 3,
            "name": "Legal Aid",
            "lat": 39.2833,
            "lng": -76.6020,
            "category": "Legal",
            "phone_number": "123-456-7890",
            "address": "789 Harbor Rd, Baltimore, MD",
            "description": "Provides free primary care services for uninsured residents.",

        },
    ]
    return render(request, "map_home.html", {"resources": resources})