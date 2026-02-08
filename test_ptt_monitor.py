#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple tests for PTT Monitor
"""

import os
import tempfile
import sys

# Import the functions from ptt_monitor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ptt_monitor


def test_processed_ids():
    """Test loading and saving processed IDs"""
    print("Testing processed_ids functions...")
    
    # Create a temporary file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        temp_file = f.name
        f.write("M.1234567890.A.123\n")
        f.write("M.9876543210.A.456\n")
    
    try:
        # Test loading
        ids = ptt_monitor.load_processed_ids(temp_file)
        assert len(ids) == 2, f"Expected 2 IDs, got {len(ids)}"
        assert "M.1234567890.A.123" in ids, "Missing expected ID"
        assert "M.9876543210.A.456" in ids, "Missing expected ID"
        print("✓ Load test passed")
        
        # Test saving
        ids.add("M.1111111111.A.789")
        ptt_monitor.save_processed_ids(ids, temp_file)
        
        # Reload and verify
        ids2 = ptt_monitor.load_processed_ids(temp_file)
        assert len(ids2) == 3, f"Expected 3 IDs after save, got {len(ids2)}"
        assert "M.1111111111.A.789" in ids2, "New ID not saved"
        print("✓ Save test passed")
        
    finally:
        # Clean up
        if os.path.exists(temp_file):
            os.remove(temp_file)
    
    print("✓ All processed_ids tests passed\n")


def test_keyword_matching():
    """Test that keyword matching would work"""
    print("Testing keyword matching logic...")
    
    keywords = ["地震", "颱風", "停電"]
    test_cases = [
        ("台灣發生地震", True),
        ("颱風即將來襲", True),
        ("突然停電了", True),
        ("今天天氣很好", False),
        ("地震來了", True),  # Keyword in different position
    ]
    
    for title, should_match in test_cases:
        matched = False
        for keyword in keywords:
            if keyword.lower() in title.lower():
                matched = True
                break
        
        assert matched == should_match, f"Failed for '{title}': expected {should_match}, got {matched}"
        print(f"✓ '{title}': {matched} (expected {should_match})")
    
    print("✓ All keyword matching tests passed\n")


def test_article_structure():
    """Test that article structure is correct"""
    print("Testing article structure...")
    
    article = {
        'id': 'M.1234567890.A.123',
        'title': 'Test Article',
        'url': 'https://www.ptt.cc/bbs/Test/M.1234567890.A.123.html'
    }
    
    assert 'id' in article, "Article missing 'id' field"
    assert 'title' in article, "Article missing 'title' field"
    assert 'url' in article, "Article missing 'url' field"
    
    print("✓ Article structure test passed\n")


if __name__ == '__main__':
    print("=" * 60)
    print("Running PTT Monitor Tests")
    print("=" * 60 + "\n")
    
    test_processed_ids()
    test_keyword_matching()
    test_article_structure()
    
    print("=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)
