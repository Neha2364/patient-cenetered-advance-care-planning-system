# ACP Care – Advance Care Planning System

A modern, responsive frontend prototype for an AI-powered Advance Care Planning (ACP) platform. This application is designed to help patients document healthcare preferences and enable healthcare professionals to monitor ACP progress through an intuitive dashboard.

> **Project Status:** Frontend Prototype Completed ✅  
> Backend integration is planned for future development.

---

## Overview

ACP Care is a healthcare web application that provides an intuitive interface for managing Advance Care Planning. The current version focuses on delivering a clean, responsive, and production-quality frontend using modern web technologies.

The application includes separate interfaces for patients and doctors, designed with a reusable component architecture to simplify future backend integration.

---

## Features Implemented

### Authentication
- Modern Sign In page
- Create Account page
- Single-page authentication flow
- Responsive split-screen layout
- Form validation UI
- Placeholder authentication (frontend only)

### Patient Dashboard
- ACP progress overview
- Progress tracker
- ACP Assistant interface
- Document section
- Activity timeline
- Notification area
- Settings navigation
- Responsive dashboard layout

### Doctor Dashboard
- Patient overview
- ACP review interface
- Analytics cards
- Patient records table
- Section completion charts
- ACP priority visualization
- Responsive dashboard layout

### UI/UX
- Premium healthcare-inspired interface
- Fully responsive design
- Reusable components
- Smooth animations
- Modern typography
- Soft shadows and glassmorphism elements
- Accessible layout
- Clean navigation

---

## Tech Stack

- React
- TypeScript
- Vite
- TanStack Router
- Tailwind CSS
- Framer Motion
- Lucide React
- shadcn/ui

---

## Project Structure

```
src/
│
├── components/
├── routes/
│   ├── index.tsx
│   ├── patient-dashboard.tsx
│   ├── doctor-dashboard.tsx
│   └── __root.tsx
│
├── lib/
├── hooks/
├── styles/
└── assets/
```

---

## Current Status

### Completed
- Frontend UI
- Responsive layouts
- Navigation
- Reusable components
- Dashboard interfaces
- Authentication screens
- Placeholder frontend data

### Planned

- Backend (Node.js + Express)
- MongoDB Database
- User Authentication
- JWT Authorization
- ACP Conversational Chatbot
- Living Will PDF Generation
- Document Storage
- Doctor-Patient Management
- Notifications
- Role-based Access Control
- API Integration
- Secure Data Persistence

---

## Installation

Clone the repository

```bash
git clone <repository-url>
```

Install dependencies

```bash
npm install
```

Start the development server

```bash
npm run dev
```

---

## Important Note

This repository currently contains the **frontend prototype only**.

All user information, dashboard statistics, chatbot conversations, and documents are represented using placeholder/mock data for UI demonstration purposes.

No backend services, APIs, databases, or authentication mechanisms have been implemented yet.

---

## Future Scope

- AI-powered ACP conversational assistant
- Secure patient authentication
- Role-based dashboards
- Healthcare document generation
- Doctor review workflow
- Database integration
- Cloud deployment
- Multilingual support
- Notification system
- Analytics and reporting

---

## License

This project is developed for academic and educational purposes.