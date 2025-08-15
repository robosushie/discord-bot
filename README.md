# User Invitation System

A full-stack application built with FastAPI backend and Streamlit UI for managing user invitations and verifications.

## Features

- **CSV Upload & Processing**: Upload CSV files with user details (email, name, college, branch, year)
- **Duplicate Prevention**: Automatically skips existing email addresses
- **Token Generation**: Generates unique 6-character verification tokens for each user
- **Email Integration**: Sends verification emails using SendGrid
- **User Management**: View all users with verification status
- **Token Refresh**: Refresh tokens for unverified users
- **User Verification**: Verify users with email and token combination
- **Token Expiry**: Configurable token expiration (default: 7 days)

## Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: Streamlit (Python)
- **Database**: PostgreSQL (Azure)
- **Email Service**: SendGrid
- **ORM**: SQLAlchemy

## Prerequisites

- Python 3.12+
- PostgreSQL database (Azure or local)
- SendGrid account and API key

## Installation

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd discord-bot
   ```

2. **Install dependencies**

   ```bash
   poetry install
   ```

3. **Configure environment variables**
   - Create a `.env` file with the following variables:
     ```env
     DATABASE_URL=postgresql://username:password@your-azure-postgres-server.postgres.database.azure.com:5432/database_name
     SENDGRID_API_KEY=your_sendgrid_api_key
     SENDGRID_FROM_EMAIL=your_verified_sender_email@domain.com
     TOKEN_EXPIRY_DAYS=7
     SECRET_KEY=your_secret_key_here
     ```

## Usage

### Starting the Application

**From the root directory**:

```bash
cd discord-bot
uvicorn app:app --reload
```

Or simply:

```bash
python app.py
```

This starts both FastAPI backend and Streamlit frontend in a single process.

**Important**: Make sure you're in the root directory (`discord-bot/`) when running the command, not in the `src/app/` directory.

### Access Points

- **Main App**: http://localhost:8000
- **API Endpoints**: http://localhost:8000/api
- **Dashboard**: http://localhost:8000/dashboard (redirects to http://localhost:8501)
- **API Documentation**: http://localhost:8000/api/docs
- **Health Check**: http://localhost:8000/health

### Using the Application

#### 1. Invitation Page

- Upload a CSV file with user details
- The CSV should contain columns: `email`, `name`, `college`, `branch`, `year`
- View processing results (total processed, newly added, skipped)
- Send verification emails to newly added users

#### 2. View Users Page

- View all users in the database
- See verification status and masked tokens
- Refresh tokens for unverified users
- Resend verification emails

#### 3. Verify User Page

- Verify users with their email and token
- Check verification status

## API Endpoints

### Base URL: `http://localhost:8000/api`

| Endpoint                   | Method | Description                        |
| -------------------------- | ------ | ---------------------------------- |
| `/`                        | GET    | Root endpoint                      |
| `/upload-csv`              | POST   | Upload and process CSV file        |
| `/send-emails`             | POST   | Send verification emails to users  |
| `/users`                   | GET    | Get all users                      |
| `/refresh-token/{user_id}` | POST   | Refresh token for a user           |
| `/verify`                  | POST   | Verify a user with email and token |

### API Documentation

Once the backend is running, visit `http://localhost:8000/api/docs` for interactive API documentation.

## Database Schema

The application creates a `users` table with the following structure:

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR UNIQUE NOT NULL,
    name VARCHAR NOT NULL,
    college VARCHAR NOT NULL,
    branch VARCHAR NOT NULL,
    year INTEGER NOT NULL,
    token VARCHAR(6) UNIQUE NOT NULL,
    is_verified BOOLEAN DEFAULT FALSE,
    token_created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);
```

## CSV Format

The CSV file should have the following columns:

```csv
email,name,college,branch,year
john.doe@example.com,John Doe,Engineering College,Computer Science,3
jane.smith@example.com,Jane Smith,Engineering College,Electrical Engineering,2
```

## Email Template

The verification email includes:

- Personalized greeting with user's name
- 6-character verification code
- Expiration information
- Professional styling

## Configuration

### Environment Variables

- `DATABASE_URL`: PostgreSQL connection string
- `SENDGRID_API_KEY`: SendGrid API key for sending emails
- `SENDGRID_FROM_EMAIL`: Verified sender email address
- `TOKEN_EXPIRY_DAYS`: Number of days before tokens expire (default: 7)
- `SECRET_KEY`: Secret key for the application

### Token Configuration

- **Length**: 6 characters (configurable in `helpers.py`)
- **Characters**: Uppercase letters (A-Z) and digits (0-9)
- **Expiry**: Configurable via environment variable
- **Uniqueness**: Guaranteed across all users

## Error Handling

The application includes comprehensive error handling for:

- Invalid CSV formats
- Database connection issues
- Email sending failures
- Token generation conflicts
- User verification errors

## Security Features

- **Token Masking**: Tokens are masked in the UI (e.g., "A\*\*\*\*Z")
- **Input Validation**: All inputs are validated and sanitized
- **SQL Injection Protection**: Uses SQLAlchemy ORM
- **CORS Configuration**: Configurable CORS settings

## Development

### Project Structure

```
discord-bot/
├── app.py                         # Main unified application (FastAPI + Streamlit)
├── src/
│   ├── app/
│   │   ├── app.py                # FastAPI application
│   │   ├── routes/
│   │   │   ├── __init__.py       # Routes package
│   │   │   └── users.py          # User-related API endpoints
│   │   └── dashboard/
│   │       ├── __init__.py       # Dashboard package
│   │       └── main.py           # Streamlit dashboard application
│   ├── models/
│   │   ├── database.py           # Database configuration
│   │   ├── user.py               # User model
│   │   └── schemas.py            # Pydantic schemas
│   └── utils/
│       └── helpers.py            # Utility functions
├── sample_users.csv               # Sample CSV file
└── README.md                      # This file
```

### Adding New Features

1. **New API Endpoints**: Add to `src/app/routes/`
2. **Database Models**: Create in `src/models/`
3. **UI Components**: Extend `src/app/dashboard/main.py`
4. **Utility Functions**: Add to `src/utils/helpers.py`

## How It Works

The application uses a single process approach:

1. **FastAPI starts** on port 8000
2. **Streamlit starts automatically** in a background thread on port 8501
3. **Dashboard routes** (`/dashboard/*`) redirect to the Streamlit instance
4. **API routes** (`/api/*`) are handled by FastAPI
5. **Single command** to start everything: `uvicorn app:app --reload`

## Troubleshooting

### Common Issues

1. **Database Connection Error**

   - Verify `DATABASE_URL` in environment variables
   - Check if PostgreSQL server is running
   - Ensure database exists and is accessible

2. **SendGrid Email Errors**

   - Verify `SENDGRID_API_KEY` is correct
   - Check if `SENDGRID_FROM_EMAIL` is verified
   - Ensure SendGrid account has sufficient credits

3. **Port Conflicts**
   - FastAPI runs on port 8000
   - Streamlit runs on port 8501
   - Ensure these ports are available

### Health Check

Use the health endpoint to check service status:

```bash
curl http://localhost:8000/health
```

### Logs

- **FastAPI**: Check console output for API logs
- **Streamlit**: Check console output for dashboard logs
- **Database**: Check PostgreSQL logs for connection issues

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For support and questions:

- Create an issue in the repository
- Check the API documentation at `/api/docs`
- Review the troubleshooting section above
