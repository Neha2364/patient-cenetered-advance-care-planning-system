import sys
sys.path.insert(0, 'ahcp-ai-service')
from app import create_session, get_session, chat, conversation_store

def run_tests():
    # 1. Kannada session
    sess_id = create_session({})
    sess = get_session(sess_id)
    sess['language'] = 'kn'
    sess['current_question'] = 3

    # Test typing English 'Female' in Kannada mode
    r_en = chat(sess_id, 'Female', 3)
    print('Kannada mode + typed English Female status:', r_en['status'])
    assert r_en['status'] == 'saved', f"Expected saved, got {r_en}"
    assert sess['patient_record']['gender'] == 'Female', f"Expected Female, got {sess['patient_record']['gender']}"

    # Test typing Kannada 'ಮಹಿಳೆ' in Kannada mode
    sess_id2 = create_session({})
    sess2 = get_session(sess_id2)
    sess2['language'] = 'kn'
    sess2['current_question'] = 3
    r_kn = chat(sess_id2, 'ಮಹಿಳೆ', 3)
    print('Kannada mode + typed Kannada ಮಹಿಳೆ status:', r_kn['status'])
    assert r_kn['status'] == 'saved', f"Expected saved, got {r_kn}"
    assert sess2['patient_record']['gender'] == 'Female', f"Expected Female, got {sess2['patient_record']['gender']}"

    # Test typing unrelated 'banana' on Q3
    sess_id3 = create_session({})
    sess3 = get_session(sess_id3)
    sess3['language'] = 'kn'
    sess3['current_question'] = 3
    r_banana = chat(sess_id3, 'banana', 3)
    print('Banana status:', r_banana['status'])
    assert r_banana['status'] == 'invalid'

    # Test typing 'Yes' on Q3 (ambiguous / invalid choice for gender)
    r_yes = chat(sess_id3, 'Yes', 3)
    print('Yes on gender status:', r_yes['status'])
    assert r_yes['status'] == 'invalid'

    # Test English session + typed Kannada 'ಪುರುಷ'
    sess_id4 = create_session({})
    sess4 = get_session(sess_id4)
    sess4['language'] = 'en'
    sess4['current_question'] = 3
    r_en_kn = chat(sess_id4, 'ಪುರುಷ', 3)
    print('English mode + typed Kannada ಪುರುಷ status:', r_en_kn['status'])
    assert r_en_kn['status'] == 'saved'
    assert sess4['patient_record']['gender'] == 'Male'

    # Test Q20 (Place of care) in Kannada mode:
    # User types 'Home'
    sess_id5 = create_session({})
    sess5 = get_session(sess_id5)
    sess5['language'] = 'kn'
    sess5['current_question'] = 20
    r_home = chat(sess_id5, 'Home', 20)
    print('Q20 typed Home status:', r_home['status'])
    assert r_home['status'] == 'saved'
    assert sess5['patient_record']['preferred_place_of_care'] == 'Home'

    # User types 'ಆಸ್ಪತ್ರೆ'
    sess_id6 = create_session({})
    sess6 = get_session(sess_id6)
    sess6['language'] = 'kn'
    sess6['current_question'] = 20
    r_hosp = chat(sess_id6, 'ಆಸ್ಪತ್ರೆ', 20)
    print('Q20 typed ಆಸ್ಪತ್ರೆ status:', r_hosp['status'])
    assert r_hosp['status'] == 'saved'
    assert sess6['patient_record']['preferred_place_of_care'] == 'Hospital'

    print('ALL DIRECT MICROSERVICE CHECKS PASSED SUCCESSFULLY!')

if __name__ == '__main__':
    run_tests()

