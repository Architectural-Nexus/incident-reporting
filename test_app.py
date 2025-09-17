#!/usr/bin/env python3
"""
Simple test script for the Incident Reports application
"""

import os
import sys
import tempfile
import unittest
from datetime import datetime

# Add the current directory to the path so we can import app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User, Incident

class TestIncidentReports(unittest.TestCase):
    def setUp(self):
        """Set up test database"""
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app = app.test_client()
        
        with app.app_context():
            db.create_all()
    
    def tearDown(self):
        """Clean up after tests"""
        with app.app_context():
            db.session.remove()
            db.drop_all()
    
    def test_home_page(self):
        """Test that the home page loads"""
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Report an Incident', response.data)
    
    def test_admin_login_page(self):
        """Test that the admin login page loads"""
        response = self.app.get('/admin/login')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Admin Login', response.data)
    
    def test_submit_incident(self):
        """Test submitting an incident report"""
        data = {
            'reporter_name': 'Test User',
            'incident_datetime': '2024-01-01T12:00',
            'location': 'Test Location',
            'persons_involved': 'Test Person',
            'description': 'Test incident description'
        }
        
        response = self.app.post('/submit_incident', data=data)
        self.assertEqual(response.status_code, 200)
        
        # Check that the incident was saved
        with app.app_context():
            incident = Incident.query.first()
            self.assertIsNotNone(incident)
            self.assertEqual(incident.reporter_name, 'Test User')
            self.assertEqual(incident.location, 'Test Location')
    
    def test_submit_incident_anonymous(self):
        """Test submitting an anonymous incident report"""
        data = {
            'incident_datetime': '2024-01-01T12:00',
            'location': 'Test Location',
            'persons_involved': 'Test Person',
            'description': 'Test incident description'
        }
        
        response = self.app.post('/submit_incident', data=data)
        self.assertEqual(response.status_code, 200)
        
        # Check that the incident was saved as anonymous
        with app.app_context():
            incident = Incident.query.first()
            self.assertIsNotNone(incident)
            self.assertEqual(incident.reporter_name, 'Anonymous')
    
    def test_submit_incident_missing_fields(self):
        """Test submitting an incident with missing required fields"""
        data = {
            'reporter_name': 'Test User',
            'incident_datetime': '2024-01-01T12:00',
            # Missing location, persons_involved, and description
        }
        
        response = self.app.post('/submit_incident', data=data)
        self.assertEqual(response.status_code, 400)
    
    def test_user_creation(self):
        """Test creating a user"""
        with app.app_context():
            user = User(username='testuser')
            user.set_password('testpass')
            db.session.add(user)
            db.session.commit()
            
            # Verify user was created
            saved_user = User.query.filter_by(username='testuser').first()
            self.assertIsNotNone(saved_user)
            self.assertTrue(saved_user.check_password('testpass'))
            self.assertFalse(saved_user.check_password('wrongpass'))

def run_tests():
    """Run the test suite"""
    print("🧪 Running Incident Reports tests...")
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestIncidentReports)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print(f"\n📊 Test Results:")
    print(f"   Tests run: {result.testsRun}")
    print(f"   Failures: {len(result.failures)}")
    print(f"   Errors: {len(result.errors)}")
    
    if result.failures:
        print(f"\n❌ Failures:")
        for test, traceback in result.failures:
            print(f"   {test}: {traceback}")
    
    if result.errors:
        print(f"\n❌ Errors:")
        for test, traceback in result.errors:
            print(f"   {test}: {traceback}")
    
    if result.wasSuccessful():
        print(f"\n✅ All tests passed!")
        return True
    else:
        print(f"\n❌ Some tests failed!")
        return False

if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1) 