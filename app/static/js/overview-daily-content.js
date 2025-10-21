(function(window, document) {
    'use strict';

    const quotes = [
    {
        "quote": "Believe you can and you're halfway there.",
        "author": "Theodore Roosevelt"
    },
    {
        "quote": "The future belongs to those who believe in the beauty of their dreams.",
        "author": "Eleanor Roosevelt"
    },
    {
        "quote": "Success is not final, failure is not fatal: it is the courage to continue that counts.",
        "author": "Winston Churchill"
    },
    {
        "quote": "Don't watch the clock; do what it does. Keep going.",
        "author": "Sam Levenson"
    },
    {
        "quote": "Everything you've ever wanted is on the other side of fear.",
        "author": "George Addair"
    },
    {
        "quote": "The way to get started is to quit talking and begin doing.",
        "author": "Walt Disney"
    },
    {
        "quote": "Act as if what you do makes a difference. It does.",
        "author": "William James"
    },
    {
        "quote": "Never give up on a dream just because of the time it will take to accomplish it.",
        "author": "Earl Nightingale"
    },
    {
        "quote": "The only way to do great work is to love what you do.",
        "author": "Steve Jobs"
    },
    {
        "quote": "Do what you can, with what you have, where you are.",
        "author": "Theodore Roosevelt"
    },
    {
        "quote": "It does not matter how slowly you go as long as you do not stop.",
        "author": "Confucius"
    },
    {
        "quote": "Opportunities don't happen. You create them.",
        "author": "Chris Grosser"
    },
    {
        "quote": "Don't let yesterday take up too much of today.",
        "author": "Will Rogers"
    },
    {
        "quote": "The secret of getting ahead is getting started.",
        "author": "Mark Twain"
    },
    {
        "quote": "Quality means doing it right when no one is looking.",
        "author": "Henry Ford"
    },
    {
        "quote": "The only limit to our realization of tomorrow is our doubts of today.",
        "author": "Franklin D. Roosevelt"
    },
    {
        "quote": "I find that the harder I work, the more luck I seem to have.",
        "author": "Thomas Jefferson"
    },
    {
        "quote": "Courage is resistance to fear, mastery of fear, not absence of fear.",
        "author": "Mark Twain"
    },
    {
        "quote": "Dream big and dare to fail.",
        "author": "Norman Vaughan"
    },
    {
        "quote": "Hardships often prepare ordinary people for an extraordinary destiny.",
        "author": "C.S. Lewis"
    },
    {
        "quote": "Don't be pushed around by the fears in your mind. Be led by the dreams in your heart.",
        "author": "Roy T. Bennett"
    },
    {
        "quote": "Believe in yourself and all that you are.",
        "author": "Christian D. Larson"
    },
    {
        "quote": "Failure is simply the opportunity to begin again, this time more intelligently.",
        "author": "Henry Ford"
    },
    {
        "quote": "You are never too old to set another goal or to dream a new dream.",
        "author": "C.S. Lewis"
    },
    {
        "quote": "Do what you feel in your heart to be right \u2013 for you\u2019ll be criticized anyway.",
        "author": "Eleanor Roosevelt"
    },
    {
        "quote": "If you're going through hell, keep going.",
        "author": "Winston Churchill"
    },
    {
        "quote": "I never dreamed about success. I worked for it.",
        "author": "Est\u00e9e Lauder"
    },
    {
        "quote": "Doubt kills more dreams than failure ever will.",
        "author": "Suzy Kassem"
    },
    {
        "quote": "We may encounter many defeats but we must not be defeated.",
        "author": "Maya Angelou"
    },
    {
        "quote": "The only person you are destined to become is the person you decide to be.",
        "author": "Ralph Waldo Emerson"
    },
    {
        "quote": "Do what you love and you'll never work a day in your life.",
        "author": "Marc Anthony"
    },
    {
        "quote": "I attribute my success to this: I never gave or took any excuse.",
        "author": "Florence Nightingale"
    },
    {
        "quote": "You miss 100% of the shots you don\u2019t take.",
        "author": "Wayne Gretzky"
    },
    {
        "quote": "Perseverance is not a long race; it is many short races one after another.",
        "author": "Walter Elliot"
    },
    {
        "quote": "A year from now you may wish you had started today.",
        "author": "Karen Lamb"
    },
    {
        "quote": "Small deeds done are better than great deeds planned.",
        "author": "Peter Marshall"
    },
    {
        "quote": "It always seems impossible until it's done.",
        "author": "Nelson Mandela"
    },
    {
        "quote": "Happiness is not something ready made. It comes from your own actions.",
        "author": "Dalai Lama"
    },
    {
        "quote": "Don't be afraid to give up the good to go for the great.",
        "author": "John D. Rockefeller"
    },
    {
        "quote": "To be successful, the first thing to do is fall in love with your work.",
        "author": "Sister Mary Lauretta"
    },
    {
        "quote": "Opportunities multiply as they are seized.",
        "author": "Sun Tzu"
    },
    {
        "quote": "What would you do if you weren't afraid?",
        "author": "Sheryl Sandberg"
    },
    {
        "quote": "Do one thing every day that scares you.",
        "author": "Eleanor Roosevelt"
    },
    {
        "quote": "The difference between a successful person and others is not lack of strength, not lack of knowledge, but rather a lack in will.",
        "author": "Vince Lombardi"
    },
    {
        "quote": "Action is the foundational key to all success.",
        "author": "Pablo Picasso"
    },
    {
        "quote": "A goal is a dream with a deadline.",
        "author": "Napoleon Hill"
    },
    {
        "quote": "The best revenge is massive success.",
        "author": "Frank Sinatra"
    },
    {
        "quote": "It\u2019s not whether you get knocked down, it\u2019s whether you get up.",
        "author": "Vince Lombardi"
    },
    {
        "quote": "Go as far as you can see; when you get there, you'll be able to see further.",
        "author": "Thomas Carlyle"
    },
    {
        "quote": "Only put off until tomorrow what you are willing to die having left undone.",
        "author": "Pablo Picasso"
    },
    {
        "quote": "Whether you think you can or think you can't, you're right.",
        "author": "Henry Ford"
    },
    {
        "quote": "Do not wait to strike till the iron is hot, but make it hot by striking.",
        "author": "William Butler Yeats"
    },
    {
        "quote": "Success is how high you bounce when you hit bottom.",
        "author": "George S. Patton"
    },
    {
        "quote": "If you want to lift yourself up, lift up someone else.",
        "author": "Booker T. Washington"
    },
    {
        "quote": "He who conquers himself is the mightiest warrior.",
        "author": "Confucius"
    },
    {
        "quote": "Work hard in silence, let your success be your noise.",
        "author": "Frank Ocean"
    },
    {
        "quote": "Life is 10% what happens to us and 90% how we react to it.",
        "author": "Charles R. Swindoll"
    },
    {
        "quote": "Success usually comes to those who are too busy to be looking for it.",
        "author": "Henry David Thoreau"
    },
    {
        "quote": "Start where you are. Use what you have. Do what you can.",
        "author": "Arthur Ashe"
    },
    {
        "quote": "The harder the conflict, the greater the triumph.",
        "author": "George Washington"
    },
    {
        "quote": "Discipline is the bridge between goals and accomplishment.",
        "author": "Jim Rohn"
    },
    {
        "quote": "Great things are done by a series of small things brought together.",
        "author": "Vincent van Gogh"
    },
    {
        "quote": "If opportunity doesn't knock, build a door.",
        "author": "Milton Berle"
    },
    {
        "quote": "Success is the sum of small efforts, repeated day in and day out.",
        "author": "Robert Collier"
    },
    {
        "quote": "Well done is better than well said.",
        "author": "Benjamin Franklin"
    },
    {
        "quote": "What you do today can improve all your tomorrows.",
        "author": "Ralph Marston"
    },
    {
        "quote": "Success seems to be connected with action. Successful people keep moving.",
        "author": "Conrad Hilton"
    },
    {
        "quote": "Great works are performed not by strength but by perseverance.",
        "author": "Samuel Johnson"
    },
    {
        "quote": "The future depends on what you do today.",
        "author": "Mahatma Gandhi"
    },
    {
        "quote": "Do not let what you cannot do interfere with what you can do.",
        "author": "John Wooden"
    },
    {
        "quote": "Hard work beats talent when talent doesn't work hard.",
        "author": "Tim Notke"
    },
    {
        "quote": "The difference between ordinary and extraordinary is that little extra.",
        "author": "Jimmy Johnson"
    },
    {
        "quote": "Success is liking yourself, liking what you do, and liking how you do it.",
        "author": "Maya Angelou"
    },
    {
        "quote": "Strive not to be a success, but rather to be of value.",
        "author": "Albert Einstein"
    },
    {
        "quote": "Do something today that your future self will thank you for.",
        "author": "Sean Patrick Flanery"
    },
    {
        "quote": "You don't have to be great to start, but you have to start to be great.",
        "author": "Zig Ziglar"
    },
    {
        "quote": "The best way to predict the future is to create it.",
        "author": "Peter Drucker"
    }
];
    const triviaItems = [
    {
        "question": "Did you know that the Philippines is home to the world's smallest active volcano?",
        "answer": "Taal Volcano in Batangas stands at only 311 meters tall but has a massive crater lake.",
        "image": "https://images.unsplash.com/photo-1633670057397-b12fc5289e96?q=80&w=1740&auto=format&fit=crop&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D"
    },
    {
        "question": "Did you know that the Banaue Rice Terraces are over 2000 years old?",
        "answer": "Carved into mountains by ancestors, these terraces are a UNESCO World Heritage site.",
        "image": "https://images.unsplash.com/photo-1711060169357-ed923c9f2156?q=80&w=1744&auto=format&fit=crop&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D"
    },
    {
        "question": "Did you know that Jeepneys are a popular form of public transport in the Philippines?",
        "answer": "Known for their vibrant decorations, jeepneys are a symbol of Philippine culture.",
        "image": "https://images.unsplash.com/photo-1589018773480-924433cdb827?q=80&w=1887&auto=format&fit=crop&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D"
    },
    {
        "question": "Did you know a Filipino engineer invented an early version of video calling in 1955?",
        "answer": "Gregorio Y. Zara patented a two-way TV-telephone system, predating Skype and FaceTime by decades.",
        "image": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRmogQHwEFE6l0YzKd5HQApWOuh7uvOokUzhA&s"
    },
    {
        "question": "Did you know the Philippines accidentally printed 800,000 winning Pepsi bottle caps in 1992?",
        "answer": "The 'Number Fever' promo caused chaos when a glitch led to 500,000 claimants demanding prizes, costing Pepsi \u20b1200 million.",
        "image": "https://images.esquiremag.ph/esquiremagph/images/2022/01/17/MicrosoftTeams-image%20(11).png"
    },
    {
        "question": "Did you know a shark species was named after 'Lord of the Rings' character Gollum?",
        "answer": "The Gollum suluensis shark, discovered in the Sulu Sea, has a darker coloration and softer body than its relatives.",
        "image": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTDI1UkjjPJJTFctRQ16qfcxLoXR8cHOKjDvw&s"
    },
    {
        "question": "Did you know the first same-sex marriage in the Philippines was held by communist rebels?",
        "answer": "In 2005, two New People\u2019s Army members exchanged vows with bullets in their hands, symbolizing commitment to their cause.",
        "image": "https://www.workers.org/world/2005/npa2.jpg"
    },
    {
        "question": "Did you know the world's largest pearl was found in the Philippines?",
        "answer": "Weighing 34 kg, the 'Pearl of Puerto' was discovered by a fisherman in Palawan and remained under his bed for 10 years.",
        "image": "https://lh6.googleusercontent.com/proxy/ljBU8FvA9QMmVfwgw_GviMtIhufB85LnsQOvtHBsC7JHU1v7Lv8pn3dqHlS5-xxyGKAgGAKwk2WHZpSYt2muLU-ImVV0lAxFRFsbDCDVUpei2VUnSzNaYPDjWh8cSZo"
    },
    {
        "question": "Did you know a prison in Palawan has no walls?",
        "answer": "Iwahig Prison allows inmates to farm, guide tours, and craft souvenirs, relying on dense jungles as a natural barrier.",
        "image": "https://southeastasiaglobe.com/wp-content/uploads/2020/02/philippine-prison_01.jpg"
    },
    {
        "question": "Did you know the Philippines created 'Little Africa' on an island?",
        "answer": "Calauit Island hosts giraffes, zebras, and African antelopes alongside endemic species like the Palawan peacock pheasant.",
        "image": "https://nojuanisanisland.com/wp-content/uploads/2015/03/dsc_7255.jpg?w=1060"
    },
    {
        "question": "Did you know a Filipina was Harvard Medical School's first female student?",
        "answer": "Fe del Mundo broke gender barriers in 1936 and later invented a bamboo incubator for rural hospitals.",
        "image": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQ-sA_Uf5BcHyZHZzg22fIULyhfeSsSE6OE_Q&s"
    },
    {
        "question": "Did you know the Philippines has a church built with egg whites?",
        "answer": "Baclayon Church in Bohol used 2 million egg whites to bind coral stones during its 1727 construction.",
        "image": "https://aroundbohol.com/wp-content/uploads/2017/05/backlayon-church-.jpg"
    },
    {
        "question": "Did you know the Philippines hosts the world's longest underground river?",
        "answer": "The Puerto Princesa Subterranean River stretches 8.2 km through limestone caves and is a UNESCO World Heritage Site.",
        "image": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQNjZMskQP6bJGxVtk3E34_k7nr55Wav_a95w&s"
    },
    {
        "question": "Did you know Manila was once home to Asia's first university?",
        "answer": "The University of Santo Tomas, founded in 1611, predates Harvard by 25 years.",
        "image": "https://upload.wikimedia.org/wikipedia/commons/7/7b/400_Year_old_Beauty.jpg"
    },
    {
        "question": "Did you know Filipinos invented the karaoke machine?",
        "answer": "Roberto del Rosario patented the Karaoke Sing-Along System in 1975, sparking a global cultural phenomenon.",
        "image": "https://upload.wikimedia.org/wikipedia/commons/2/24/Blind_Bulake%C3%B1a_beggar_vocalist_with_Karaoke_microphone_in_Santa_Maria_01.jpg"
    },
    {
        "question": "Did you know the Philippine flag signals war when flown upside down?",
        "answer": "The red field flies atop during conflicts, as seen in 2010 when the U.S. accidentally inverted it during a ceremony.",
        "image": "https://i.redd.it/hcfr6kmzuif81.jpg"
    },
    {
        "question": "Did you know a Filipino pilot landed a bomb-damaged plane with 272 passengers?",
        "answer": "Captain Ed Reyes safely landed PAL Flight 434 in 1994 using only engine thrust after terrorists damaged its controls.",
        "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/cb/Philippine_Airlines_Boeing_747-283B_%28M%29%3B_EI-BWF%2C_December_1988_%285669249917%29.jpg/1024px-Philippine_Airlines_Boeing_747-283B_%28M%29%3B_EI-BWF%2C_December_1988_%285669249917%29.jpg"
    },
    {
        "question": "Did you know the Philippines has the world's longest Christmas season?",
        "answer": "Festivities begin in September and last until January, featuring lantern festivals and extended caroling.",
        "image": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRU4r4z8jyn0WowAr0bvCrD3TcSlZxTbmCGEw&s"
    },
    {
        "question": "Did you know a Filipina animated Disney's 'Finding Nemo' character Dory?",
        "answer": "Gini Santos, a UST graduate, led the animation team for the forgetful blue fish voiced by Ellen DeGeneres.",
        "image": "https://upload.wikimedia.org/wikipedia/commons/5/5f/Angus-maclane_Buscando_a_Dory_premiere.jpg"
    },
    {
        "question": "Did you know the Philippines has a bamboo organ from 1824?",
        "answer": "Las Pi\u00f1as' St. Joseph Parish Church houses a unique organ with 1,031 pipes made from bamboo.",
        "image": "https://pia.gov.ph/uploads/2023/03/3c18991cf602a62c50b4b98881c9e701.jpg"
    },
    {
        "question": "Did you know the Philippine eagle is the world's largest eagle species?",
        "answer": "With a 2-meter wingspan, this critically endangered bird is found only in the Philippines.:cite[4]:cite[9]",
        "image": "https://gttp.images.tshiftcdn.com/376750/x/0/a-philippine-eagle-in-the-philippine-eagle-center.jpg?ar=1.91%3A1&w=1200&fit=crop"
    },
    {
        "question": "Did you know Texas was once called 'Nuevas Filipinas'?",
        "answer": "Spanish missionaries used the name in the 18th century to gain royal favor, referencing the Philippines' colonial status.",
        "image": "https://images.esquiremag.ph/esquiremagph/images/2020/06/11/esquire-newphilippines-mainimage.jpg"
    },
    {
        "question": "Did you know the Philippines has a 'Christmas Capital'?",
        "answer": "San Fernando City holds giant lantern festivals, with some parols (lanterns) reaching 20 meters in diameter.",
        "image": "https://media.cnn.com/api/v1/images/stellar/prod/131223090151-1-philippines-christmas-lanterns.jpg?q=w_1200,h_803,x_0,y_0,c_fill/h_447"
    },
    {
        "question": "Did you know Corregidor Island was WWII's 'Pacific War Memorial'?",
        "answer": "This strategic fortress in Manila Bay witnessed fierce battles between Japanese and Filipino-American forces.",
        "image": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTQgh6OXbEUL9scpjwyAEk_I3KCqdQg-auM9g&s"
    },
    {
        "question": "Did you know Vigan's streets are lined with Spanish-era houses?",
        "answer": "Calle Crisologo's cobblestone paths and horse-drawn carriages make it a UNESCO World Heritage Site.",
        "image": "https://shoestringdiary.wordpress.com/wp-content/uploads/2025/02/vigan-calle_crisologo02-ssd-cover.jpg?w=1140"
    },
    {
        "question": "Did you know the Chocolate Hills change color with the seasons?",
        "answer": "Bohol's 1,268 limestone mounds turn lush green in the rainy months and fade to chocolate brown in summer heat.",
        "image": "https://upload.wikimedia.org/wikipedia/commons/a/ac/Bohol_Hills%2C_Chocolate_Hills%2C_Philippines.jpg"
    },
    {
        "question": "Did you know Apo Reef is the world's second-largest contiguous coral system?",
        "answer": "Spanning 34 square kilometers off Occidental Mindoro, Apo Reef shelters more than 380 species of coral and fish.",
        "image": "https://upload.wikimedia.org/wikipedia/commons/1/10/Aerial_Photo_of_Apo_Menor_of_Apo_Reef_Natural_Park.jpg"
    },
    {
        "question": "Did you know Mount Pinatubo now hides a turquoise crater lake?",
        "answer": "After its 1991 eruption reshaped Luzon, Mount Pinatubo filled with rainwater to form the 2.5 kilometer wide Lake Pinatubo.",
        "image": "https://upload.wikimedia.org/wikipedia/commons/2/23/Crater_Lake_at_the_Mount_Pinatubo_Caldera_in_the_Philippines.jpg"
    },
    {
        "question": "Did you know Malacanang Palace has stood beside the Pasig River since 1750?",
        "answer": "Originally a Spanish summer house, the palace became the official residence of Philippine presidents in 1935.",
        "image": "https://images.esquiremag.ph/esquiremagph/images/gallery/6997/MAIN-malacanang.jpg"
    },
    {
        "question": "Did you know Surigao del Sur's Enchanted River appears bottomless?",
        "answer": "Hinatuan's Enchanted River plunges over 25 meters deep with crystal blue water fed by an underground spring.",
        "image": "https://upload.wikimedia.org/wikipedia/commons/2/22/Enchanted_River%2C_Hinatuan%2C_Surigao_del_Sur.jpg"
    },
    {
        "question": "Did you know Pangasinan's Hundred Islands number more than 120 islets?",
        "answer": "The national park protects 16 square kilometers of limestone outcrops and marine life in Lingayen Gulf.",
        "image": "https://upload.wikimedia.org/wikipedia/commons/3/3d/Hundred_Island.jpg"
    },
    {
        "question": "Did you know Mayon Volcano is famed for its near-perfect cone?",
        "answer": "Rising 2,462 meters over Albay, Mayon's symmetrical slopes are the result of centuries of stratovolcanic eruptions.",
        "image": "https://upload.wikimedia.org/wikipedia/commons/3/3b/Mayon_Volcano%2C_Albay%2C_Philippines.jpg"
    },
    {
        "question": "Did you know Bacolod's MassKara Festival began as a morale booster?",
        "answer": "Launched in 1980, the smiling masks of MassKara uplifted Negros Occidental during a sugar crisis and a tragic ferry sinking.",
        "image": "https://upload.wikimedia.org/wikipedia/commons/e/e9/MASSKARA_FESTIVAL_01.jpg"
    },
    {
        "question": "Did you know the country's first National Living Treasure for tattooing still inks by hand?",
        "answer": "Kalinga elder Whang-Od uses pomelo thorns and charcoal to hand-tap batok designs on visitors in Buscalan, Mountain Province.",
        "image": "https://upload.wikimedia.org/wikipedia/commons/d/d2/Apo_Whang-od%27s_house_in_Buscalan%2C_Tinglayan%2C_Kalinga.jpg"
    },
    {
        "question": "Did you know Manila's Intramuros walls stretch nearly three kilometers?",
        "answer": "The 16th century Spanish fortress once wrapped the entire colonial capital, complete with moats, bastions, and stone gates.",
        "image": "https://upload.wikimedia.org/wikipedia/commons/6/6e/Intramuros%2C_Manila_%E2%80%94_speaks_the_heart_of_history_louder.jpg"
    },
    {
        "question": "Did you know Mount Apo is the highest peak in the Philippines?",
        "answer": "Towering 2,954 meters above Davao, Mount Apo shelters rare species like the Philippine eagle and pitcher plants.",
        "image": "https://upload.wikimedia.org/wikipedia/commons/5/5b/A_Father%27s_Sacrifice%2C_Carrying_His_Son_Through_Rain_to_the_Entry_Trail_of_Mt._Apo%2C_Philippines%27_Highest_Peak.jpg"
    },
    {
        "question": "Did you know the Philippine tarsier's eyes are bigger than its brain?",
        "answer": "The nocturnal primate of Bohol and Mindanao has enormous eyes fixed in place, so it rotates its head almost 180 degrees.",
        "image": "https://upload.wikimedia.org/wikipedia/commons/1/13/Babytarsier.jpg"
    },
    {
        "question": "Did you know Puerto Princesa's Iwahig River glows with fireflies at night?",
        "answer": "Mangrove trees along the river host thousands of fireflies whose synchronized flashes light up eco-friendly night cruises.",
        "image": "https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?auto=format&fit=crop&w=1200&q=80"
    },
    {
        "question": "Did you know Baguio blooms during the Panagbenga Flower Festival?",
        "answer": "Every February, giant floral floats and street dancers celebrate the season of blooming in the City of Pines.",
        "image": "https://upload.wikimedia.org/wikipedia/commons/4/43/Baguio_Panagbenga_Festival.jpg"
    },
    {
        "question": "Did you know Siargao is called the surfing capital of the Philippines?",
        "answer": "The island's Cloud 9 break draws international surfers with its thick right-hand barrels every September.",
        "image": "https://upload.wikimedia.org/wikipedia/commons/e/e9/Catching_the_Wave.jpg"
    },
    {
        "question": "Did you know Camiguin has more volcanoes than towns?",
        "answer": "The island province counts seven volcanoes across only five municipalities, earning it the nickname Island Born of Fire.",
        "image": "https://upload.wikimedia.org/wikipedia/commons/b/b5/Camiguin_Island%2C_as_seen_from_Macajalar_Bay.jpg"
    },
    {
        "question": "Did you know Butuan's balangay boats predate Magellan by centuries?",
        "answer": "Archaeologists unearthed 1,000-year-old wooden balangay in Agusan del Norte, proof of early maritime trade networks.",
        "image": "https://upload.wikimedia.org/wikipedia/commons/f/f7/Balangay_Boat_Building_Site_Butuan_City.jpg"
    },
    {
        "question": "Did you know Cebu's Sinulog Festival honors the Santo Nino with a dance for two beats forward and one back?",
        "answer": "Millions join the January fiesta, waving bright props while chanting Pit Senyor in the historic Queen City of the South.",
        "image": "https://upload.wikimedia.org/wikipedia/commons/d/da/Sinulog_Festival_%282023%29_contingents_in_street_dance_01.jpg"
    },
    {
        "question": "Did you know Donsol, Sorsogon is famed for seasonal whale shark encounters?",
        "answer": "From November to June, the coastal town hosts regulated butanding tours that let visitors snorkel beside gentle giants.",
        "image": "https://upload.wikimedia.org/wikipedia/commons/0/04/Butanding_Whale_Shark_%28Donsol%2C_Sorsogon%29_%28794278440%29.jpg"
    },
    {
        "question": "Did you know Las Casas Filipinas de Acuzar rebuilds heritage mansions by the beach?",
        "answer": "The Bagac, Bataan resort relocates salvaged ancestral homes and restores them as a living museum of Filipino architecture.",
        "image": "https://upload.wikimedia.org/wikipedia/commons/2/26/Casa_Mexico%2C_Las_Casas_Filipinas_de_Acuzar%2C_Bataan.JPG"
    }
];

    const DAY_IN_MS = 24 * 60 * 60 * 1000;

    function selectDailyItem(storageKey, dateKey, items) {
        const today = new Date().toDateString();
        const storedItem = localStorage.getItem(storageKey);
        const storedDate = localStorage.getItem(dateKey);

        if (storedItem && storedDate === today) {
            try {
                return JSON.parse(storedItem);
            } catch (error) {
                console.warn('Unable to parse stored item for', storageKey, error);
            }
        }

        const item = items[Math.floor(Math.random() * items.length)];
        localStorage.setItem(storageKey, JSON.stringify(item));
        localStorage.setItem(dateKey, today);
        return item;
    }

    function updateQuote() {
        const quoteText = document.getElementById('quote');
        const authorText = document.getElementById('author');
        if (!quoteText || !authorText) {
            return;
        }

        const dailyQuote = selectDailyItem('dailyQuote', 'quoteDate', quotes);
        quoteText.textContent = dailyQuote.quote;
        authorText.textContent = '\u2014 ' + dailyQuote.author;
    }

    function updateTrivia() {
        const questionEl = document.getElementById('trivia-question');
        const answerEl = document.getElementById('trivia-answer');
        const imageContainer = document.getElementById('trivia-image');
        if (!questionEl || !answerEl || !imageContainer) {
            return;
        }

        const trivia = selectDailyItem('dailyTrivia', 'triviaDate', triviaItems);
        questionEl.textContent = trivia.question;
        answerEl.textContent = trivia.answer;
        imageContainer.innerHTML = `<img src="${trivia.image}" alt="Trivia image" style="width:100%; height:300px; object-fit:cover; border-radius:10px;" onerror="this.onerror=null;this.src='https://dummyimage.com/800x300/cccccc/000000&text=Image+Not+Found'" />`;
        imageContainer.classList.remove('hidden');
        imageContainer.classList.add('show');
    }

    function scheduleAtMidnight(callback) {
        const now = new Date();
        const nextMidnight = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1, 0, 0, 0);
        const delay = nextMidnight.getTime() - now.getTime();

        setTimeout(() => {
            callback();
            setInterval(callback, DAY_IN_MS);
        }, delay);
    }

    function init() {
        updateQuote();
        updateTrivia();
        scheduleAtMidnight(updateQuote);
        scheduleAtMidnight(updateTrivia);
    }

    window.OverviewDailyContent = {
        init,
        updateQuote,
        updateTrivia
    };
})(window, document);
