"""
Alias for the demo-data seed command.

Usage: python manage.py populate
"""
from .seed_initial_data import Command as SeedInitialDataCommand


class Command(SeedInitialDataCommand):
    help = "Populate the database with realistic EMS demo data."
