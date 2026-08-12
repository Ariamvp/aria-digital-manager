import streamlit as st
import os
from PIL import Image, ImageDraw, ImageFont
import openai
import textwrap
import io
from dotenv import load_dotenv

load_dotenv()

# Initialize OpenAI (Make sure OPENAI_API_KEY is in your .env file)
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

st.set_page_config(page_title="A.R.I.A. Digital Manager", layout="centered", page_icon="🚀")

# ==========================================
# HELPER FUNCTIONS
# ==========================================
def call_openai(prompt):
    """Generic function to call OpenAI quickly and cheaply."""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini", # Extremely cheap and fast
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
        img_path = f"assets/{template_file}"
        image = Image.open(img_path).convert("RGBA")
        draw = ImageDraw.Draw(image)
        width, height = image.size
        
        # Load fonts
        try:
            font_headline = ImageFont.truetype(font_path, 85)
            font_subtext = ImageFont.truetype(font_path, 45)
            font_brand = ImageFont.truetype(font_path, 35)
        except:
            st.error("Font file not found! Check assets folder.")
            return None

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
# CUSTOM CSS
# ==========================================
st.markdown("""
<style>
    .stApp { background-color: #F8FAFC; }
    .main-header { font-size: 2.2rem; color: #0F172A; font-weight: 800; text-align: center; margin-bottom: 0.5rem; }
    .sub-header { font-size: 1.1rem; color: #64748B; text-align: center; margin-bottom: 2rem; }
    .stButton > button {
        background: linear-gradient(135deg, #16A34A 0%, #15803D 100%);
        color: white; border: none; border-radius: 8px; font-weight: 700; padding: 12px 24px; width: 100%;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { background-color: white; border-radius: 8px 8px 0 0; padding: 12px 24px; font-weight: 600; }
    .stTabs [aria-selected="true"] { background-color: #16A34A; color: white; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header"> A.R.I.A. Digital Manager</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Your AI Marketing & Reputation Assistant</div>', unsafe_allow_html=True)

# ==========================================
# TABS NAVIGATION
# ==========================================
tab_poster, tab_review, tab_inquiry = st.tabs(["🎨 Poster Maker", "⭐ Review Responder", "️ Inquiry Responder"])

# ==========================================
# TAB 1: POSTER MAKER
# ==========================================
with tab_poster:
    st.subheader("Create Professional Social Media Posters")
    col1, col2 = st.columns([1, 1])

    with col1:
        business_name = st.text_input("Business Name", value="My Bakery", key="poster_biz")
        template_choice = st.selectbox("Choose Template", ["festive.png", "sale.png", "clean.png"], key="poster_temp")
        headline = st.text_input("Main Headline (Big Text)", value="50% OFF", max_chars=15, key="poster_head")
        subtext = st.text_input("Subtext (Details)", value="This Weekend Only!", max_chars=40, key="poster_sub")
        platform = st.selectbox("Target Platform", ["Instagram", "Facebook", "WhatsApp Status"], key="poster_plat")
        gen_poster_btn = st.button("✨ Generate Poster & Caption", type="primary")

    with col2:
        if gen_poster_btn:
            if not headline or not business_name:
                st.error("Please fill in Business Name and Headline.")
            else:
                with st.spinner("Designing poster..."):
                    font_path = "assets/fonts/Montserrat-Bold.ttf" 
                    poster_image = create_poster(template_choice, headline, subtext, business_name, font_path)
                    
                    if poster_image:
                        st.image(poster_image, caption="Your Generated Poster", use_column_width=True)
                        buf = io.BytesIO()
                        poster_image.save(buf, format="JPEG", quality=90)
                        st.download_button(label="📥 Download Image", data=buf.getvalue(), file_name=f"{business_name}_poster.jpg", mime="image/jpeg", use_container_width=True)

                with st.spinner("Writing AI Caption..."):
                    caption = call_openai(f"Write a short, engaging Instagram caption for {business_name} about '{headline} - {subtext}'. Include 5 relevant hashtags.")
                    st.text_area("AI Caption:", value=caption, height=150)

# ==========================================
# TAB 2: REVIEW RESPONDER
# ==========================================
with tab_review:
    st.subheader("Reply to Google/Social Media Reviews")
    st.markdown("Paste a customer review below, and A.R.I.A. will write a professional, polite response.")
    
    col1, col2 = st.columns(2)
    with col1:
        reviewer_name = st.text_input("Reviewer Name", value="Customer")
        rating = st.selectbox("Star Rating", [1, 2, 3, 4, 5], index=4)
    with col2:
        biz_name_review = st.text_input("Your Business Name", value="My Bakery")
        owner_name = st.text_input("Your Name (for sign-off)", value="Manager")

    review_text = st.text_area("Paste the Customer Review Here", height=150, placeholder="e.g., The food was good but the service was very slow...")
    
    if st.button("✨ Generate Professional Reply", type="primary"):
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
                st.text_area("Copy this reply:", value=response, height=200)

# ==========================================
# TAB 3: INQUIRY RESPONDER
# ==========================================
with tab_inquiry:
    st.subheader("Reply to Customer Inquiries (WhatsApp/Email)")
    st.markdown("Paste a customer question, and A.R.I.A. will draft a sales-focused reply.")
    
    col1, col2 = st.columns(2)
    with col1:
        customer_name = st.text_input("Customer Name", value="Friend")
        biz_name_inq = st.text_input("Your Business Name", value="My Bakery")
    with col2:
        product_service = st.text_input("What do you sell?", value="Cakes and Pastries")
        contact_info = st.text_input("Your Phone/Address", value="Call us at 9876543210")

    inquiry_text = st.text_area("Paste the Customer's Question", height=150, placeholder="e.g., Hi, do you have eggless chocolate cakes available for tomorrow?")
    
    if st.button("✨ Generate Sales Reply", type="primary"):
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
                st.text_area("Copy this reply:", value=response, height=200)