import streamlit as st
import os
from PIL import Image, ImageDraw, ImageFont
import openai
import textwrap
import io
from dotenv import load_dotenv

load_dotenv()

# Initialize OpenAI
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

st.set_page_config(page_title="A.R.I.A. Digital Manager", layout="centered", page_icon="🚀")

# ==========================================
# HELPER FUNCTIONS
# ==========================================
def call_openai(prompt):
    """Generic function to call OpenAI quickly and cheaply."""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": "You are an expert marketing and customer service assistant for Indian small businesses. Keep responses professional, polite, and concise."},
                      {"role": "user", "content": prompt}],
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {e}"

def create_poster(template_file, headline, subtext, business_name, font_path):
    """Overlays text onto a background template using Pillow."""
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        img_path = os.path.join(base_dir, "assets", template_file)
        
        # Check if template exists
        if not os.path.exists(img_path):
            st.error(f"Template not found: {img_path}")
            return None
            
        image = Image.open(img_path).convert("RGBA")
        draw = ImageDraw.Draw(image)
        width, height = image.size
        
        # Try to load custom font, fall back to default if not found
        try:
            full_font_path = os.path.join(base_dir, font_path)
            font_headline = ImageFont.truetype(full_font_path, 85)
            font_subtext = ImageFont.truetype(full_font_path, 45)
            font_brand = ImageFont.truetype(full_font_path, 35)
        except Exception as font_error:
            # Use default font if custom font not found
            font_headline = ImageFont.load_default()
            font_subtext = ImageFont.load_default()
            font_brand = ImageFont.load_default()
            st.warning(f"⚠️ Using default font. Custom font path: {full_font_path}")

        def draw_centered_text(y_pos, text, font, color, shadow_color="black"):
            lines = textwrap.fill(text, width=20).split('\n')
            line_height = font.getbbox("A")[3] + 10
            total_height = len(lines) * line_height
            current_y = y_pos - (total_height / 2)

            for line in lines:
                bbox = draw.textbbox((0, 0), line, font=font)
                text_width = bbox[2] - bbox[0]
                x = (width - text_width) / 2
                draw.text((x+3, current_y+3), line, font=font, fill=shadow_color)
                draw.text((x, current_y), line, font=font, fill=color)
                current_y += line_height

        draw_centered_text(height * 0.35, headline.upper(), font_headline, "white")
        draw_centered_text(height * 0.55, subtext, font_subtext, "#FFD700") 
        draw_centered_text(height * 0.85, business_name.upper(), font_brand, "white")

        return image.convert("RGB")
    except Exception as e:
        st.error(f"Error creating poster: {e}")
        return None

# ==========================================
# ENHANCED CUSTOM CSS
# ==========================================
st.markdown("""
<style>
    /* Global Styles */
    .stApp { background-color: #F8FAFC; }
    .main-header { font-size: 2.2rem; color: #0F172A; font-weight: 800; text-align: center; margin-bottom: 0.5rem; }
    .sub-header { font-size: 1.1rem; color: #64748B; text-align: center; margin-bottom: 2rem; }
    
    /* Button Styling */
    .stButton > button {
        background: linear-gradient(135deg, #16A34A 0%, #15803D 100%);
        color: white; border: none; border-radius: 8px; font-weight: 700; padding: 12px 24px; width: 100%;
    }
    
    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { background-color: white; border-radius: 8px 8px 0 0; padding: 12px 24px; font-weight: 600; }
    .stTabs [aria-selected="true"] { background-color: #16A34A; color: white; }
    
    /* INPUT FIELDS - ENHANCED VISIBILITY */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div > div {
        background-color: #FFFFFF !important;
        border: 2px solid #3B82F6 !important;
        border-radius: 8px !important;
        padding: 12px 16px !important;
        font-size: 15px !important;
        color: #0F172A !important;
        transition: all 0.3s ease !important;
    }
    
    /* Input Focus State - Green Border */
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus,
    .stSelectbox > div > div > div:focus {
        border-color: #16A34A !important;
        border-width: 3px !important;
        box-shadow: 0 0 0 4px rgba(22, 163, 74, 0.15) !important;
        background-color: #F0FDF4 !important;
    }
    
    /* Input Hover State */
    .stTextInput > div > div > input:hover,
    .stTextArea > div > div > textarea:hover {
        border-color: #60A5FA !important;
        background-color: #EFF6FF !important;
    }
    
    /* Labels - Bold and Clear */
    .stTextInput label, .stTextArea label, .stSelectbox label {
        color: #1E293B !important;
        font-weight: 700 !important;
        font-size: 14px !important;
        margin-bottom: 8px !important;
    }
    
    /* Section Headers */
    .stSubheader {
        color: #0F172A !important;
        font-weight: 700 !important;
        margin-bottom: 20px !important;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">🔥 A.R.I.A. Digital Manager</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Your AI Marketing & Reputation Assistant</div>', unsafe_allow_html=True)

# ==========================================
# TABS NAVIGATION
# ==========================================
tab_poster, tab_review, tab_inquiry = st.tabs(["🎨 Poster Maker", "⭐ Review Responder", " Inquiry Responder"])

# ==========================================
# TAB 1: POSTER MAKER
# ==========================================
with tab_poster:
    st.subheader("Create Professional Social Media Posters")
    col1, col2 = st.columns([1, 1])

    with col1:
        business_name = st.text_input("Business Name", value="My Bakery", max_chars=100, key="poster_biz_name", 
                                     help="Enter your business or shop name")
        template_choice = st.selectbox("Choose Template", ["festive.png", "sale.png", "clean.png"], key="poster_template",
                                      help="Select a background template style")
        headline = st.text_input("Main Headline (Big Text)", value="50% OFF", max_chars=50, key="poster_headline",
                                help="Short, punchy text that grabs attention")
        subtext = st.text_input("Subtext (Details)", value="This Weekend Only!", max_chars=100, key="poster_subtext",
                               help="Additional details about your offer")
        platform = st.selectbox("Target Platform", ["Instagram", "Facebook", "WhatsApp Status"], key="poster_platform",
                               help="Where will you post this?")
        gen_poster_btn = st.button("✨ Generate Poster & Caption", type="primary", key="poster_generate_btn")

    with col2:
        if gen_poster_btn:
            if not headline or not business_name:
                st.error("Please fill in Business Name and Headline.")
            else:
                with st.spinner("Designing poster..."):
                    font_path = "assets/fonts/Poppins-Bold.ttf"  # Updated to Poppins
                    poster_image = create_poster(template_choice, headline, subtext, business_name, font_path)
                    
                    # Only try to display if poster was created successfully
                    if poster_image is not None:
                        st.image(poster_image, caption="Your Generated Poster", use_column_width=True)
                        buf = io.BytesIO()
                        poster_image.save(buf, format="JPEG", quality=90)
                        st.download_button(label="📥 Download Image", data=buf.getvalue(), file_name=f"{business_name}_poster.jpg", mime="image/jpeg", use_container_width=True, key="poster_download")

                        with st.spinner("Writing AI Caption..."):
                            caption = call_openai(f"Write a short, engaging Instagram caption for {business_name} about '{headline} - {subtext}'. Include 5 relevant hashtags.")
                            st.text_area("AI Caption:", value=caption, height=150, key="poster_caption",
                                        help="Copy this caption for your social media post")

# ==========================================
# TAB 2: REVIEW RESPONDER
# ==========================================
with tab_review:
    st.subheader("Reply to Google/Social Media Reviews")
    st.markdown("Paste a customer review below, and A.R.I.A. will write a professional, polite response.")
    
    col1, col2 = st.columns(2)
    with col1:
        reviewer_name = st.text_input("Reviewer Name", value="Customer", max_chars=100, key="review_reviewer")
        rating = st.selectbox("Star Rating", [1, 2, 3, 4, 5], index=4, key="review_rating")
    with col2:
        biz_name_review = st.text_input("Your Business Name", value="My Bakery", max_chars=100, key="review_biz_name")
        owner_name = st.text_input("Your Name (for sign-off)", value="Manager", max_chars=50, key="review_owner")

    review_text = st.text_area("Paste the Customer Review Here", height=150, max_chars=1000, 
                              placeholder="e.g., The food was good but the service was very slow...", key="review_text")
    
    if st.button("✨ Generate Professional Reply", type="primary", key="review_generate_btn"):
        if review_text:
            with st.spinner("Writing response..."):
                prompt = f"""
                Act as the owner of {biz_name_review}. 
                A customer named {reviewer_name} gave us {rating} stars and wrote: "{review_text}"
                
                Write a polite, professional reply. 
                - If rating is 4 or 5: Thank them warmly and invite them back.
                - If rating is 1, 2, or 3: Apologize sincerely, acknowledge their specific complaint, and offer to make it right.
                Keep it under 100 words. Sign off as {owner_name}.
                """
                response = call_openai(prompt)
                st.success("Reply Generated!")
                st.text_area("Copy this reply:", value=response, height=200, key="review_response",
                            help="Copy this response to paste on Google/Facebook")

# ==========================================
# TAB 3: INQUIRY RESPONDER
# ==========================================
with tab_inquiry:
    st.subheader("Reply to Customer Inquiries (WhatsApp/Email)")
    st.markdown("Paste a customer question, and A.R.I.A. will draft a sales-focused reply.")
    
    col1, col2 = st.columns(2)
    with col1:
        customer_name = st.text_input("Customer Name", value="Friend", max_chars=100, key="inq_customer")
        biz_name_inq = st.text_input("Your Business Name", value="My Bakery", max_chars=100, key="inq_biz_name")
    with col2:
        product_service = st.text_input("What do you sell?", value="Cakes and Pastries", max_chars=150, key="inq_product")
        contact_info = st.text_input("Your Phone/Address", value="Call us at 9876543210", max_chars=200, key="inq_contact")

    inquiry_text = st.text_area("Paste the Customer's Question", height=150, max_chars=1000, 
                               placeholder="e.g., Hi, do you have eggless chocolate cakes available for tomorrow?", key="inq_text")
    
    if st.button("✨ Generate Sales Reply", type="primary", key="inq_generate_btn"):
        if inquiry_text:
            with st.spinner("Drafting reply..."):
                prompt = f"""
                Act as a sales representative for {biz_name_inq} which sells {product_service}.
                A customer named {customer_name} asked: "{inquiry_text}"
                
                Write a friendly, helpful, and sales-oriented reply. Answer their question clearly, highlight your quality, and include a clear Call to Action to order. 
                End with the contact info: {contact_info}. Keep it under 150 words.
                """
                response = call_openai(prompt)
                st.success("Reply Drafted!")
                st.text_area("Copy this reply:", value=response, height=200, key="inq_response",
                            help="Copy this reply to send via WhatsApp or Email")