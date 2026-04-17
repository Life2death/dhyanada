"""Format government schemes and MSP alerts for WhatsApp."""
from datetime import date
from typing import Optional


def format_schemes_reply(schemes: list[dict], lang: str = "mr") -> str:
    """
    Format eligible government schemes for farmer.

    Args:
        schemes: List of eligible scheme dicts from repository
        lang: "mr" for Marathi, "en" for English

    Returns:
        Formatted WhatsApp message
    """
    if lang == "mr":
        return _format_schemes_marathi(schemes)
    else:
        return _format_schemes_english(schemes)


def format_no_schemes_reply(lang: str = "mr") -> str:
    """Format message when no eligible schemes found."""
    if lang == "mr":
        return (
            "😔 खेद आहे, आपल्या प्रोफाईलसाठी सध्या कोई योजना उपलब्ध नाहीत।\n\n"
            "आपल्या नोंदणी तपशील तपासा (वय, जमीनचे आकार, पिकें)।\n"
            "तहसील कार्यालय किंवा KVK संस्थेशी संपर्क साधा।"
        )
    else:
        return (
            "😔 Sorry, no schemes are currently available for your profile.\n\n"
            "Please verify your registration details (age, land size, crops).\n"
            "Contact your local agricultural office or KVK."
        )


def format_msp_alert_subscription(commodity: str, threshold: float, lang: str = "mr") -> str:
    """Format MSP alert subscription confirmation."""
    if lang == "mr":
        return (
            f"✅ MSP अलर्ट सेट केला\n\n"
            f"🌾 पीक: {commodity.capitalize()}\n"
            f"📊 निर्धारित किंमत: ₹{threshold:,.0f}/क्विंटल\n\n"
            f"जेव्हा {commodity} की किंमत ₹{threshold:,.0f} पार करेल, तर आपल्याला सूचित केले जाईल। "
            f"अलर्ट हटवायचे? \"MSP अलर्ट बंद करा\" असे लिहा।"
        )
    else:
        return (
            f"✅ MSP Alert Set\n\n"
            f"🌾 Commodity: {commodity.capitalize()}\n"
            f"📊 Target Price: ₹{threshold:,.0f}/quintal\n\n"
            f"You'll be notified when {commodity} price reaches ₹{threshold:,.0f}. "
            f"To remove alert, reply 'Turn off MSP alert'."
        )


def format_msp_alert_triggered(commodity: str, current_msp: float, threshold: float, lang: str = "mr") -> str:
    """Format MSP alert notification when price is reached."""
    if lang == "mr":
        return (
            f"🚨 MSP अलर्ट — {commodity.upper()}\n\n"
            f"📈 किंमत आपल्या लक्ष्य तक पहुंची गई!\n"
            f"🌾 पीक: {commodity.capitalize()}\n"
            f"💹 वर्तमान MSP: ₹{current_msp:,.0f}/क्विंटल\n"
            f"📊 आपका लक्ष्य मूल्य: ₹{threshold:,.0f}/क्विंटल\n\n"
            f"💡 अब बेचने की सोचें! तहसील मंडी से संपर्क करें।\n"
            f"📞 यदि और विवरण चाहिए तो उत्तर दें।"
        )
    else:
        return (
            f"🚨 MSP Alert — {commodity.upper()}\n\n"
            f"📈 Price has reached your target!\n"
            f"🌾 Commodity: {commodity.capitalize()}\n"
            f"💹 Current MSP: ₹{current_msp:,.0f}/quintal\n"
            f"📊 Your Target: ₹{threshold:,.0f}/quintal\n\n"
            f"💡 Consider selling now! Contact your local mandi.\n"
            f"📞 Reply if you need more information."
        )


def _format_schemes_marathi(schemes: list[dict]) -> str:
    """Format schemes in Marathi."""
    if not schemes:
        return format_no_schemes_reply(lang="mr")

    msg = "🎯 आपके लिए उपलब्ध योजनाएं:\n\n"

    for i, scheme in enumerate(schemes[:5], 1):  # Top 5 schemes
        benefit = scheme.get("annual_benefit", "")
        deadline = scheme.get("application_deadline", "")
        description = scheme.get("description", "")

        msg += f"{i}️⃣ {scheme['scheme_name']}\n"
        msg += f"   💰 लाभ: {benefit}\n"

        if deadline:
            deadline_obj = deadline if isinstance(deadline, date) else date.fromisoformat(str(deadline))
            msg += f"   📅 अंतिम तारीख: {deadline_obj.strftime('%d-%m-%Y')}\n"

        msg += f"   📝 {description[:80]}...\n\n"

    msg += "💡 कोई प्रश्न? तहसील कृषि अधिकारी से संपर्क करें।\n"
    msg += "☎️ PM-KISAN आवेदन: pmkisan.gov.in"

    return msg


def _format_schemes_english(schemes: list[dict]) -> str:
    """Format schemes in English."""
    if not schemes:
        return format_no_schemes_reply(lang="en")

    msg = "🎯 Available Schemes for You:\n\n"

    for i, scheme in enumerate(schemes[:5], 1):  # Top 5 schemes
        benefit = scheme.get("annual_benefit", "")
        deadline = scheme.get("application_deadline", "")
        description = scheme.get("description", "")

        msg += f"{i}️⃣ {scheme['scheme_name']}\n"
        msg += f"   💰 Benefit: {benefit}\n"

        if deadline:
            deadline_obj = deadline if isinstance(deadline, date) else date.fromisoformat(str(deadline))
            msg += f"   📅 Deadline: {deadline_obj.strftime('%d-%m-%Y')}\n"

        msg += f"   📝 {description[:80]}...\n\n"

    msg += "💡 Have questions? Contact your agricultural officer.\n"
    msg += "☎️ Apply for PM-KISAN: pmkisan.gov.in"

    return msg
