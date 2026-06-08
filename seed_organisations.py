from accounts.models import Organisation

organisations = [
    {
        "name": "WeSafe Nigeria",
        "state": "Lagos",
        "city": "Lagos",
        "address": "14 Bode Thomas Street, Surulere, Lagos",
        "phone": "+234 801 234 5678",
        "email": "info@wesafe.ng",
    },
    {
        "name": "Shield Initiative",
        "state": "Abuja",
        "city": "Abuja",
        "address": "Plot 22 Cadastral Zone, Wuse II, Abuja",
        "phone": "+234 802 345 6789",
        "email": "contact@shieldinitiative.org.ng",
    },
    {
        "name": "VoiceUp Foundation",
        "state": "Rivers",
        "city": "Port Harcourt",
        "address": "7 Aba Road, Port Harcourt, Rivers State",
        "phone": "+234 803 456 7890",
        "email": "support@voiceupfoundation.ng",
    },
    {
        "name": "SafeHaven Kano",
        "state": "Kano",
        "city": "Kano",
        "address": "3 Ibrahim Taiwo Road, Kano",
        "phone": "+234 804 567 8901",
        "email": "help@safehavenkano.org",
    },
    {
        "name": "Restore Hope Enugu",
        "state": "Enugu",
        "city": "Enugu",
        "address": "9 Ogui Road, Enugu",
        "phone": "+234 805 678 9012",
        "email": "info@restorehope.org.ng",
    },
    {
        "name": "NorthStar Care",
        "state": "Bauchi",
        "city": "Bauchi",
        "address": "15 Jos Road, Bauchi",
        "phone": "+234 806 789 0123",
        "email": "northstarcare@gmail.com",
    },
    {
        "name": "JusticeLink Kaduna",
        "state": "Kaduna",
        "city": "Kaduna",
        "address": "21 Ahmadu Bello Way, Kaduna",
        "phone": "+234 807 890 1234",
        "email": "info@justicelinkkaduna.org",
    },
    {
        "name": "RiverGuard Foundation",
        "state": "Akwa Ibom",
        "city": "Uyo",
        "address": "5 Oron Road, Uyo, Akwa Ibom",
        "phone": "+234 808 901 2345",
        "email": "riverguard@foundation.ng",
    },
    {
        "name": "Anambra SafeNet",
        "state": "Anambra",
        "city": "Onitsha",
        "address": "12 New Market Road, Onitsha, Anambra",
        "phone": "+234 809 012 3456",
        "email": "safenet@anambra.org.ng",
    },
    {
        "name": "IbadanCare Alliance",
        "state": "Oyo",
        "city": "Ibadan",
        "address": "8 Ring Road, Ibadan, Oyo State",
        "phone": "+234 810 123 4567",
        "email": "info@ibadancare.org",
    },
    {
        "name": "BenCity Women's Trust",
        "state": "Edo",
        "city": "Benin",
        "address": "3 Sapele Road, Benin City, Edo State",
        "phone": "+234 811 234 5678",
        "email": "bencitywomen@trust.ng",
    },
    {
        "name": "PeacePoint Jos",
        "state": "Plateau",
        "city": "Jos",
        "address": "17 Yakubu Gowon Way, Jos, Plateau State",
        "phone": "+234 812 345 6789",
        "email": "peacepoint@jos.org.ng",
    },
    {
        "name": "OwerriHelps Foundation",
        "state": "Imo",
        "city": "Owerri",
        "address": "6 Douglas Road, Owerri, Imo State",
        "phone": "+234 813 456 7890",
        "email": "info@owerrihelps.org",
    },
    {
        "name": "Abeokuta Women's Network",
        "state": "Ogun",
        "city": "Abeokuta",
        "address": "10 Ibara Road, Abeokuta, Ogun State",
        "phone": "+234 814 567 8901",
        "email": "awnetwork@ogun.org.ng",
    },
]

created = skipped = 0
for data in organisations:
    obj, was_created = Organisation.objects.get_or_create(
        name=data["name"],
        defaults={
            "state": data["state"],
            "city": data["city"],
            "address": data["address"],
            "phone": data["phone"],
            "email": data["email"],
            "is_active": True,
        }
    )
    if was_created:
        created += 1
    else:
        skipped += 1

print(f"{created} organisations created, {skipped} skipped.")
