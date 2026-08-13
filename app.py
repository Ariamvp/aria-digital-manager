import streamlit as st
import os
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import openai
import textwrap
import io
import requests
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

st.set_page_config(page_title="A.R.I.A. Smart Poster Engine", layout="centered", page_icon="🚀")

# ==========================================
# DYNAMIC RESOURCE LOADER
# ==========================================
GOOGLE_FONTS_RAW = "https://raw.githubusercontent.com/google/fonts/main"

def get_available_fonts():
    """Popular free fonts from Google Fonts"""
    return {
        "Poppins (Modern/Bold)": {
            "url": f"{GOOGLE_FONTS_RAW}/ofl/poppins/Poppins%5Bwght%5D.ttf",
        },
        "Playfair Display (Elegant)": {
            "url": f"{GOOGLE_FONTS_RAW}/ofl/playfairdisplay/PlayfairDisplay%5Bwght%5D.ttf",
        },
        "Fredoka One (Playful)": {
            "url": f"{GOOGLE_FONTS_RAW}/ofl/fredoka/Fredoka%5Bwght%5D.ttf",
        },
        "Roboto (Clean)": {
            "url": f"{GOOGLE_FONTS_RAW}/apache/roboto/Roboto%5Bwght%5D.ttf",
        },
        "Oswald (Strong)": {
            "url": f"{GOOGLE_FONTS_RAW}/ofl/oswald/Oswald%5Bwght%5D.ttf",
        },
        "Lobster (Decorative)": {
            "url": f"{GOOGLE_FONTS_RAW}/ofl/lobster/Lobster-Regular.ttf",
        },
        "Bebas Neue (Impact)": {
            "url": f"{GOOGLE_FONTS_RAW}/ofl/bebasneue/BebasNeue-Regular.ttf",
        }
    }

def download_font(font_name, font_url):
    """Download font from Google Fonts GitHub"""
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        font_dir = os.path.join(base_dir, "assets", "fonts")
        os.makedirs(font_dir, exist_ok=True)
        
        # Clean filename for saving
        safe_name = font_name.replace(" ", "_").replace("(", "").replace(")", "")
        font_path = os.path.join(font_dir, f"{safe_name}.ttf")
        
        if os.path.exists(font_path):
            return font_path
        
        response = requests.get(font_url, timeout=10)
        if response.status_code == 200:
            with open(font_path, 'wb') as f:
                f.write(response.content)
            return font_path
    except Exception as e:
        st.warning(f"⚠️ Could not download font: {font_name}")
    return None

def fetch_unsplash_images(query="festival", count=6):
    """Fetch free high-quality images from Unsplash Official API"""
    access_key = os.getenv("UNSPLASH_ACCESS_KEY")
    
    if not access_key:
        st.error("❌ Unsplash API key not found! Please add UNSPLASH_ACCESS_KEY to Streamlit Secrets.")
        return []
    
    images = []
    try:
        url = "https://api.unsplash.com/search/photos"
        params = {
            "query": query,
            "per_page": count,
            "orientation": "squarish",
            "client_id": access_key
        }
        
        response = requests.get(url, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            
            for result in results:
                img_url = result['urls']['regular']
                img_response = requests.get(img_url, timeout=15)
                if img_response.status_code == 200:
                    images.append(img_response.content)
        else:
            st.error(f"Unsplash API error: {response.status_code}")
            
    except Exception as e:
        st.error(f"Error fetching images: {e}")
    
    return images

# ==========================================
# SMART TEMPLATE ENGINE
# ==========================================
def get_style_config(style_name):
    """Returns font, colors, and layout settings based on chosen style."""
    if "Modern" in style_name or "Bold" in style_name:
        return {
            "font_key": "Poppins (Modern/Bold)",
            "headline_color": "#FFFFFF", "subtext_color": "#FFD700", "brand_color": "#FFFFFF",
            "outline_color": "#000000", "shadow_strength": 5
        }
    elif "Elegant" in style_name or "Traditional" in style_name:
        return {
            "font_key": "Playfair Display (Elegant)",
            "headline_color": "#F8FAFC", "subtext_color": "#FCD34D", "brand_color": "#F8FAFC",
            "outline_color": "#1E293B", "shadow_strength": 3
        }
    elif "Playful" in style_name or "Fun" in style_name:
        return {
            "font_key": "Fredoka One (Playful)",
            "headline_color": "#FFFFFF", "subtext_color": "#FCA5A5", "brand_color": "#FFFFFF",
            "outline_color": "#7F1D1D", "shadow_strength": 4
        }
    elif "Minimal" in style_name or "Clean" in style_name:
        return {
            "font_key": "Roboto (Clean)",
            "headline_color": "#FFFFFF", "subtext_color": "#E5E7EB", "brand_color": "#FFFFFF",
            "outline_color": "#111827", "shadow_strength": 4
        }
    elif "Impact" in style_name or "Strong" in style_name:
        return {
            "font_key": "Bebas Neue (Impact)",
            "headline_color": "#FFFFFF", "subtext_color": "#FBBF24", "brand_color": "#FFFFFF",
            "outline_color": "#000000", "shadow_strength": 6
        }
    else:
        return {
            "font_key": "Poppins (Modern/Bold)",
            "headline_color": "#FFFFFF", "subtext_color": "#FFD700", "brand_color": "#FFFFFF",
            "outline_color": "#000000", "shadow_strength": 5
        }

def draw_text_with_outline(draw, position, text, font, fill_color, outline_color, outline_width=4):
    """Draws text with professional outline for maximum readability."""
    x, y = position
    for adj in range(-outline_width, outline_width + 1):
        for opp in range(-outline_width, outline_width + 1):
            if adj != 0 or opp != 0:
                draw.text((x + adj, y + opp), text, font=font, fill=outline_color)
    draw.text((x, y), text, font=font, fill=fill_color)

def create_smart_poster(base_image, headline, subtext, business_name, style_name, font_path=None):
    """The core engine that adapts to the image and style."""
    try:
        image = base_image.convert("RGBA").resize((1080, 1080))
        draw = ImageDraw.Draw(image)
        width, height = image.size
        
        if style_name == "User Upload":
            enhancer = ImageEnhance.Brightness(image)
            image = enhancer.enhance(0.5)
            draw = ImageDraw.Draw(image)
            config = {
                "headline_color": "#FFFFFF", "subtext_color": "#FFD700", "brand_color": "#FFFFFF",
                "outline_color": "#000000", "shadow_strength": 5
            }
        else:
            config = get_style_config(style_name)

        try:
            if font_path and os.path.exists(font_path):
                font_headline = ImageFont.truetype(font_path, 120)
                font_subtext = ImageFont.truetype(font_path, 60)
                font_brand = ImageFont.truetype(font_path, 45)
            else:
                font_headline = ImageFont.load_default()
                font_subtext = ImageFont.load_default()
                font_brand = ImageFont.load_default()
                st.warning("⚠️ Using default font. Download may be needed.")
        except Exception:
            font_headline = ImageFont.load_default()
            font_subtext = ImageFont.load_default()
            font_brand = ImageFont.load_default()

        def draw_centered_smart(y_pos, text, font, color, outline_width):
            max_chars = 16 if font.size > 100 else 24
            lines = textwrap.fill(text, width=max_chars).split('\n')
            line_height = font.getbbox("A")[3] + 15
            total_height = len(lines) * line_height
            current_y = y_pos - (total_height / 2)

            for line in lines:
                bbox = draw.textbbox((0, 0), line, font=font)
                text_width = bbox[2] - bbox[0]
                x = (width - text_width) / 2
                draw_text_with_outline(draw, (x, current_y), line, font, color, config["outline_color"], outline_width)
                current_y += line_height

        if "Elegant" in style_name or "Traditional" in style_name:
            draw_centered_smart(height * 0.30, headline.upper(), font_headline, config["headline_color"], config["shadow_strength"])
            draw_centered_smart(height * 0.55, subtext, font_subtext, config["subtext_color"], config["shadow_strength"])
            draw_centered_smart(height * 0.88, business_name.upper(), font_brand, config["brand_color"], config["shadow_strength"])
        else:
            draw_centered_smart(height * 0.35, headline.upper(), font_headline, config["headline_color"], config["shadow_strength"])
            draw_centered_smart(height * 0.58, subtext, font_subtext, config["subtext_color"], config["shadow_strength"])
            draw_centered_smart(height * 0.85, business_name.upper(), font_brand, config["brand_color"], config["shadow_strength"])

        return image.convert("RGB")
    except Exception as e:
        st.error(f"Engine Error: {e}")
        return None

# ==========================================
# AI CAPTION GENERATOR
# ==========================================
def call_openai(prompt):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": "You are an expert marketing assistant for Indian small businesses."},
                      {"role": "user", "content": prompt}],
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {e}"

# ==========================================
# UI & CSS
# ==========================================
st.markdown("""
<style>
    .stApp { background-color: #F8FAFC; }
    .main-header { font-size: 2.2rem; color: #0F172A; font-weight: 800; text-align: center; }
    .sub-header { font-size: 1.1rem; color: #64748B; text-align: center; margin-bottom: 2rem; }
    .stButton > button {
        background: linear-gradient(135deg, #16A34A 0%, #15803D 100%);
        color: white; border: none; border-radius: 8px; font-weight: 700; padding: 12px 24px; width: 100%;
    }
    .stTextInput > div > div > input, .stTextArea > div > div > textarea, .stSelectbox > div > div > div {
        background-color: #FFFFFF !important; border: 2px solid #3B82F6 !important; border-radius: 8px !important;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">🎨 A.R.I.A. Smart Poster Engine</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">AI-Powered Designs • Free Fonts • Unlimited Templates</div>', unsafe_allow_html=True)

tab_poster, tab_review, tab_inquiry = st.tabs(["🎨 Smart Poster", "⭐ Review Responder", "💬 Inquiry Responder"])

# ==========================================
# TAB 1: SMART POSTER ENGINE
# ==========================================
with tab_poster:
    st.subheader("Create Professional Social Media Posters")
    
    with st.sidebar:
        st.markdown("### 🎨 Design Options")
        
        bg_source = st.radio("Background Source:", 
                            ["📦 Pre-made Templates", "🌐 Fetch from Unsplash (Free)", "📤 Upload Your Own"],
                            key="bg_source")
        
        # ✅ FIXED: Exact emoji match for "Upload Your Own"
        uploaded_image = None
        if bg_source == "📤 Upload Your Own":
            uploaded_image = st.file_uploader("📤 Upload your photo", type=["jpg", "png", "jpeg"], 
                                             key="upload_img", help="Upload a photo of your product, shop, or dish")
        
        if bg_source == "🌐 Fetch from Unsplash (Free)":
            unsplash_query = st.text_input("Search for background:", 
                                           value="indian festival lights",
                                           help="e.g., 'diwali', 'food', 'restaurant', 'sale', 'onam'")
            if st.button("🔄 Load Free Backgrounds", type="primary"):
                with st.spinner("Fetching beautiful free images from Unsplash..."):
                    images = fetch_unsplash_images(unsplash_query, count=6)
                    if images:
                        st.session_state['unsplash_images'] = images
                        st.success(f"✅ Loaded {len(images)} backgrounds!")
                    else:
                        st.error("Could not fetch images. Check API key or try different search terms.")
        
        if bg_source == "📦 Pre-made Templates":
            template_choice = st.selectbox("Choose Template:", ["festive.png", "sale.png", "clean.png"])
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        business_name = st.text_input("Business Name", value="My Bakery", max_chars=100, key="poster_biz_name")
        
        style_options = [
            "Bold & Modern (Sales/Offers)",
            "Elegant & Traditional (Festivals/Weddings)", 
            "Fun & Playful (Kids/Food/Casual)",
            "Minimal & Clean (Professional)",
            "Strong & Impact (Headlines)"
        ]
        
        design_style = st.selectbox("Design Style (Auto-adapts fonts & colors):", style_options, key="poster_style")
        headline = st.text_input("Main Headline", value="50% OFF", max_chars=50, key="poster_headline")
        subtext = st.text_input("Subtext (Details)", value="This Weekend Only!", max_chars=100, key="poster_subtext")
        
        gen_poster_btn = st.button("✨ Generate Smart Poster", type="primary", key="poster_generate_btn")

    with col2:
        if gen_poster_btn:
            if not headline or not business_name:
                st.error("Please fill in Business Name and Headline.")
            elif bg_source == "📤 Upload Your Own" and not uploaded_image:
                st.error("Please upload an image first!")
            else:
                with st.spinner("🎨 Smart Engine designing your poster..."):
                    if bg_source == "📤 Upload Your Own":
                        base_img = Image.open(uploaded_image)
                        style_name = "User Upload"
                        font_path = None
                        
                    elif bg_source == "🌐 Fetch from Unsplash (Free)":
                        if 'unsplash_images' in st.session_state:
                            selected_idx = st.selectbox("Select Background:", range(len(st.session_state['unsplash_images'])), key="unsplash_select")
                            base_img = Image.open(io.BytesIO(st.session_state['unsplash_images'][selected_idx]))
                            style_name = design_style
                            font_path = None
                        else:
                            st.info("👆 Click 'Load Free Backgrounds' in the sidebar first!")
                            base_img = None
                            style_name = ""
                            font_path = None
                    else:
                        base_dir = os.path.dirname(os.path.abspath(__file__))
                        img_path = os.path.join(base_dir, "assets", template_choice)
                        base_img = Image.open(img_path)
                        style_name = design_style
                        
                        # ✅ IMPROVED: Robust font downloading using config mapping
                        fonts_dict = get_available_fonts()
                        config = get_style_config(style_name)
                        font_key = config["font_key"]
                        font_url = fonts_dict[font_key]["url"]
                        font_path = download_font(font_key, font_url)
                    
                    if base_img:
                        poster_image = create_smart_poster(base_img, headline, subtext, business_name, style_name, font_path)
                        
                        if poster_image is not None:
                            st.image(poster_image, caption="Your Generated Poster", use_container_width=True)
                            buf = io.BytesIO()
                            poster_image.save(buf, format="JPEG", quality=95)
                            st.download_button(label="📥 Download High-Quality Image", 
                                             data=buf.getvalue(), 
                                             file_name=f"{business_name}_poster.jpg", 
                                             mime="image/jpeg", 
                                             use_container_width=True, 
                                             key="poster_download")

                            with st.spinner("✍️ Writing AI Caption..."):
                                caption = call_openai(f"Write engaging Instagram caption for {business_name} about '{headline} - {subtext}'. Include 5 hashtags.")
                                st.text_area("AI Caption:", value=caption, height=150, key="poster_caption")

# ==========================================
# TAB 2: REVIEW RESPONDER
# ==========================================
with tab_review:
    st.subheader("Reply to Google/Social Media Reviews")
    st.markdown("Paste a customer review, and A.R.I.A. writes a professional response.")
    
    col1, col2 = st.columns(2)
    with col1:
        reviewer_name = st.text_input("Reviewer Name", value="Customer", max_chars=100, key="review_reviewer")
        rating = st.selectbox("Star Rating", [1, 2, 3, 4, 5], index=4, key="review_rating")
    with col2:
        biz_name_review = st.text_input("Your Business Name", value="My Bakery", max_chars=100, key="review_biz_name")
        owner_name = st.text_input("Your Name", value="Manager", max_chars=50, key="review_owner")

    review_text = st.text_area("Paste Review Here", height=150, max_chars=1000, 
                              placeholder="e.g., The food was good but service was slow...", key="review_text")
    
    if st.button("✨ Generate Reply", type="primary", key="review_generate_btn"):
        if review_text:
            with st.spinner("Writing response..."):
                prompt = f"Act as owner of {biz_name_review}. Customer {reviewer_name} gave {rating} stars: '{review_text}'. Write polite professional reply. If 4-5 stars: thank warmly. If 1-3: apologize sincerely. Under 100 words. Sign as {owner_name}."
                response = call_openai(prompt)
                st.success("Reply Generated!")
                st.text_area("Copy this reply:", value=response, height=200, key="review_response")

# ==========================================
# TAB 3: INQUIRY RESPONDER
# ==========================================
with tab_inquiry:
    st.subheader("Reply to Customer Inquiries")
    st.markdown("Paste customer question, A.R.I.A. drafts sales-focused reply.")
    
    col1, col2 = st.columns(2)
    with col1:
        customer_name = st.text_input("Customer Name", value="Friend", max_chars=100, key="inq_customer")
        biz_name_inq = st.text_input("Your Business Name", value="My Bakery", max_chars=100, key="inq_biz_name")
    with col2:
        product_service = st.text_input("What do you sell?", value="Cakes and Pastries", max_chars=150, key="inq_product")
        contact_info = st.text_input("Contact Info", value="Call 9876543210", max_chars=200, key="inq_contact")

    inquiry_text = st.text_area("Customer's Question", height=150, max_chars=1000, 
                               placeholder="e.g., Do you have eggless cakes?", key="inq_text")
    
    if st.button("✨ Generate Reply", type="primary", key="inq_generate_btn"):
        if inquiry_text:
            with st.spinner("Drafting reply..."):
                prompt = f"Act as sales rep for {biz_name_inq} selling {product_service}. Customer {customer_name} asked: '{inquiry_text}'. Write friendly sales reply with CTA. End with: {contact_info}. Under 150 words."
                response = call_openai(prompt)
                st.success("Reply Drafted!")
                st.text_area("Copy this reply:", value=response, height=200, key="inq_response")