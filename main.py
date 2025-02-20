import streamlit as st
import requests
import re
import openai
 
openai.api_key = st.secrets['OPENAI_KEY']

def get_book_details(title):
    """
    Uses the Google Books API to fetch book details such as cover art, authors, and average rating.
    """
    # Optionally, add a GOOGLE_BOOKS_KEY to your st.secrets if you have one:
    google_books_key = st.secrets.get('GOOGLE_BOOKS_KEY', None)
    
    params = {
        'q': f'intitle:{title}',
        'maxResults': 1,
    }
    if google_books_key:
        params['key'] = google_books_key

    response = requests.get('https://www.googleapis.com/books/v1/volumes', params=params)
    if response.status_code == 200:
        data = response.json()
        if data.get('totalItems', 0) > 0 and data.get('items'):
            item = data['items'][0]
            volume_info = item.get('volumeInfo', {})
            image_links = volume_info.get('imageLinks', {})
            cover_url = image_links.get('thumbnail')
            authors = volume_info.get('authors', ["Unknown"])
            average_rating = volume_info.get('averageRating', None)
            
            cover_data = None
            if cover_url:
                try:
                    image_response = requests.get(cover_url)
                    if image_response.status_code == 200:
                        cover_data = image_response.content
                except Exception as e:
                    print(f"Error fetching image: {e}")
            return cover_data, authors, average_rating
    return None, None, None

def parse_openai_response(response_text):
    """
    Parses the OpenAI response into a preamble, a list of recommendations, and a postamble.
    Expected format for each recommendation:
      1. "Book Title" by Author Name - additional info...
    """
    # Regex pattern to capture recommendations in the expected format
    pattern = r'\d+\.\s"([^"]+)"\sby\s([^-\n]+)-\s(.+)$'
    
    # Split the response into lines
    lines = response_text.strip().split('\n')
    
    # Identify where recommendations start and end
    start_idx = next((i for i, line in enumerate(lines) if re.match(pattern, line)), None)
    end_idx = next((i for i in reversed(range(len(lines))) if re.match(pattern, lines[i])), None)
    
    preamble = "\n".join(lines[:start_idx]).strip() if start_idx is not None else ""
    recommendations_text = "\n".join(lines[start_idx:end_idx+1]).strip() if start_idx is not None and end_idx is not None else ""
    postamble = "\n".join(lines[end_idx+1:]).strip() if end_idx is not None and end_idx + 1 < len(lines) else ""
    
    # Extract recommendations using regex
    matches = re.findall(pattern, recommendations_text, re.MULTILINE)
    parsed_results = []
    for match in matches:
        title, author, description = match
        parsed_results.append({
            'title': title.strip(),
            'author': author.strip(),
            'description': description.strip()
        })
    return preamble, parsed_results, postamble

st.title("What Should I Read?")

st.markdown("### Tell us about your reading tastes")
# A single large text area for a detailed description
reading_input = st.text_area(
    "Share your favorite books, genres you enjoy, and what you're looking for in your next read.",
    placeholder="For example: I love immersive worlds like those in magical realism, classics with a twist, or modern narratives that make me think..."
)

# Optional: a separate input for preferred genres if you want to highlight this
preferred_genres = st.text_input(
    "Preferred genres (optional)",
    placeholder="e.g., Fantasy, Mystery, Sci-Fi"
)

if st.button("Get Book Recommendations"):
    if reading_input.strip() == "":
        st.warning("Please share a bit about your reading preferences to get a recommendation!")
    else:
        # Build the prompt for OpenAI
        genre_text = f"My preferred genres are {preferred_genres}. " if preferred_genres.strip() else ""
        prompt = (
            f"{genre_text}Here is some background about my reading tastes: {reading_input.strip()}.\n\n"
            "Based on this, please provide 4 book recommendations. "
            "Begin with a short, witty preamble that ties my interests to the suggestions. "
            "Then, list each recommendation on a new line in the following format:\n"
            '1. "Book Title" by Author Name - a brief description of why this book suits my tastes.\n'
            "End with a light postamble. Please avoid using asterisks or markdown formatting."
        )
        
        with st.spinner("Fetching recommendations..."):
            chat_completion = openai.ChatCompletion.create(
                messages=[
                    {"role": "user", "content":  "You are a helpful assistant. " + prompt}
                ],
                model="gpt-3.5-turbo",
            )
        response_text = chat_completion.choices[0].message.content
        st.write("### Recommendation Details")
        preamble, parsed_results, postamble = parse_openai_response(response_text)
        
        if preamble:
            st.write(preamble)
            st.markdown("---")
        
        # Display each recommendation
        for result in parsed_results:
            title = result['title']
            author = result['author']
            description = result['description']
            
            cover_data, book_authors, average_rating = get_book_details(title)
            
            col1, col2 = st.columns([1, 3])
            with col1:
                if cover_data:
                    st.image(cover_data, width=100)
                else:
                    st.text("Cover art not found")
            with col2:
                st.subheader(f"{title}")
                st.write(f"**by {author}**")
                if average_rating:
                    st.write(f"Average Rating: {average_rating} / 5")
                st.write(description)
            st.markdown("---")
        
        if postamble:
            st.write(postamble)
