from django.shortcuts import render


def custom_404(request, exception):
    return render(request, "404.html", status=404)


def custom_403(request, exception=None):
    return render(request, "403.html", status=403)


def support_view(request):
    return render(request, "support.html")


def faq_view(request):
    faq_items = [
        {
            "question": "How does Chakravyuh detect fraudulent calls?",
            "answer": "Chakravyuh uses AI-driven voice and behavior analytics to score calls in real time and flag anomalous patterns.",
        },
        {
            "question": "Can I integrate with existing telecom systems?",
            "answer": "Yes. We support API and webhook-based integrations to connect with call routing, CRM, and risk platforms.",
        },
        {
            "question": "What data is required to start?",
            "answer": "You can begin with call metadata and audio samples. Additional data sources improve accuracy over time.",
        },
        {
            "question": "Is the platform compliant with security standards?",
            "answer": "We follow industry best practices and support SOC 2-aligned controls and GDPR-ready data handling.",
        },
        {
            "question": "How fast can we onboard?",
            "answer": "Most teams can onboard within a few days using our guided setup and documentation.",
        },
    ]
    return render(request, "faq.html", {"faq_items": faq_items})
