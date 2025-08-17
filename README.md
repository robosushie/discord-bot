# 🤖 User Invitation System + Discord Bot

A unified backend system that combines a FastAPI-based user invitation system with an **automatic Discord verification bot**. Perfect for managing community access with email verification and automatic role assignment.

## 🏗️ **Architecture**

- **Backend**: FastAPI + Discord Bot (unified service)
- **Database**: PostgreSQL (Azure)
- **Email Service**: SendGrid
- **Authentication**: API Key (x-api-key header)
- **Frontend**: Streamlit (local development)

## 🚀 **Features**

### Backend API

- ✅ CSV upload and user management
- ✅ Email verification system
- ✅ Token generation and expiry
- ✅ User CRUD operations
- ✅ SendGrid integration

### Discord Bot (NEW!)

- ✅ **Automatic verification on join** - Bot triggers immediately when someone joins
- ✅ **Timeout enforcement** - Users get kicked if they don't verify in time (configurable)
- ✅ **Auto-role assignment** - Gives "Member" role after successful verification
- ✅ **DM verification** - Sends verification requirements via private message
- ✅ **Admin commands** - Check status, force verify, set timeouts
- ✅ **Automatic cleanup** - Removes unverified users automatically

## 📁 **Project Structure**

```
discord-bot/
├── src/
│   ├── app/
│   │   ├── app.py              # Main FastAPI app + Discord bot
│   │   ├── dependencies.py     # API key authentication
│   │   └── routes/
│   │       └── users.py        # User management endpoints
│   ├── models/
│   │   ├── database.py         # Database connection
│   │   ├── user.py             # User model
│   │   └── schemas.py          # Pydantic schemas
│   ├── utils/
│   │   └── helpers.py          # Utility functions
│   └── discord_bot/
│       └── bot.py              # Discord bot implementation
├── app.py                      # Main entry point
├── Dockerfile                  # Container configuration
└── pyproject.toml             # Dependencies
```

## 🛠️ **Setup & Installation**

### 1. **Install Dependencies**

```bash
# Install Poetry if not already installed
pip install poetry

# Install project dependencies
poetry install
```

### 2. **Environment Configuration**

Create a `.env` file based on `env.example`:

```env
# Database Configuration
DB_HOST=your-postgres-host
DB_PORT=5432
DB_USER=your-username
DB_PASSWORD=your-password
DB_NAME=your-database
DB_SSL=true

# SendGrid Configuration
SENDGRID_API_KEY=your-sendgrid-key
SENDGRID_FROM_EMAIL=your-verified-email

# Application Configuration
TOKEN_EXPIRY_DAYS=7
SECRET_KEY=your-super-secret-api-key

# Discord Bot Configuration
DISCORD_TOKEN=your-discord-bot-token
MEMBER_ROLE_NAME=Member
VERIFICATION_TIMEOUT=300
```

### 3. **Discord Bot Setup**

1. Create a Discord application at [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a bot and get the token
3. Invite bot to your server with these permissions:
   - **Manage Roles** (to assign Member role)
   - **Kick Members** (to remove unverified users)
   - **Send Messages** (to send verification DMs)
   - **Use Slash Commands** (for admin commands)
4. Create a "Member" role in your server (or change `MEMBER_ROLE_NAME` in `.env`)

## 🚀 **Running the System**

### **Simple Command (Recommended)**

```bash
uvicorn app:app --reload
```

This starts:

- **FastAPI Backend** at `http://localhost:8000`
- **Discord Bot** automatically in background
- **API endpoints** at `/api/*`
- **API docs** at `http://localhost:8000/api/docs`

## 🌐 **API Endpoints**

All endpoints require `x-api-key` header with your `SECRET_KEY`.

| Method   | Endpoint                  | Description                  |
| -------- | ------------------------- | ---------------------------- |
| `GET`    | `/api/users`              | Get all users                |
| `POST`   | `/api/upload-csv`         | Upload CSV with user data    |
| `POST`   | `/api/send-emails`        | Send verification emails     |
| `POST`   | `/api/verify`             | Verify user with email/token |
| `POST`   | `/api/verify-discord`     | **Discord bot verification** |
| `POST`   | `/api/refresh-token/{id}` | Refresh user token           |
| `DELETE` | `/api/{id}`               | Delete specific user         |
| `DELETE` | `/api/all`                | Delete all users             |

## 🤖 **Discord Bot Features**

### **Automatic Verification Flow**

1. **User joins server** → Bot immediately sends verification DM
2. **User has X minutes** (default: 5) to verify email + token
3. **Success** → User gets "Member" role, full server access
4. **Failure/Timeout** → User gets automatically kicked

### **Admin Commands**

| Command                | Description                        | Permission |
| ---------------------- | ---------------------------------- | ---------- |
| `/verification_status` | Check pending verifications        | Admin only |
| `/force_verify @user`  | Manually verify a user             | Admin only |
| `/set_timeout X`       | Set verification timeout (minutes) | Admin only |

### **Configuration Options**

- **`MEMBER_ROLE_NAME`**: Role to assign after verification (default: "Member")
- **`VERIFICATION_TIMEOUT`**: Time limit in seconds (default: 300 = 5 minutes)

## 🐳 **Docker Deployment**

### **Build Image**

```bash
docker build -t your-username/discord-bot:latest .
```

### **Push to Docker Hub**

```bash
docker login
docker push your-username/discord-bot:latest
```

### **Run Locally**

```bash
docker run -p 8000:8000 --env-file .env your-username/discord-bot:latest
```

## ☁️ **Azure VM Deployment**

### **1. Build and Push Docker Image**

```bash
# Build the image
docker build -t your-username/discord-bot:latest .

# Push to Docker Hub
docker push your-username/discord-bot:latest
```

### **2. Deploy to Azure VM**

```bash
# SSH into your Azure VM
ssh username@your-vm-ip

# Pull and run the image
docker pull your-username/discord-bot:latest
docker run -d -p 8000:8000 --env-file .env --name discord-bot your-username/discord-bot:latest
```

### **3. Environment Variables on VM**

Create `.env` file on your VM with all required variables:

- Database credentials
- SendGrid API key
- Discord bot token
- SECRET_KEY

## 🔐 **Security Features**

- **API Key Authentication**: All endpoints protected with `x-api-key` header
- **Token Expiry**: Configurable token expiration (default: 7 days)
- **Input Validation**: Pydantic models for request validation
- **Database Security**: Parameterized queries to prevent SQL injection
- **Discord Permissions**: Bot only has necessary permissions for verification

## 📊 **Frontend (Streamlit)**

The Streamlit frontend provides a web interface for:

- CSV upload and processing
- User management
- Email sending
- System monitoring

**Note**: Frontend is for local development only. In production, use the API endpoints directly.

## 🔧 **Configuration Options**

### **Token Expiry**

```env
TOKEN_EXPIRY_DAYS=7  # Change to desired number of days
```

### **Discord Bot Settings**

```env
MEMBER_ROLE_NAME=Member          # Role to assign after verification
VERIFICATION_TIMEOUT=300         # Time limit in seconds (5 minutes)
```

### **API Base URL**

The Discord bot will use the same host as the FastAPI backend by default.

## 🚨 **Troubleshooting**

### **Discord Bot Not Starting**

- Check `DISCORD_TOKEN` in environment variables
- Ensure bot has proper permissions in Discord server
- Verify `SECRET_KEY` is set correctly
- Check bot is invited to server with correct permissions

### **Users Not Getting Verified**

- Ensure "Member" role exists in Discord server
- Check bot has "Manage Roles" permission
- Verify API endpoint is accessible from Discord
- Check logs for verification errors

### **Database Connection Issues**

- Verify database credentials in `.env`
- Check network connectivity to Azure PostgreSQL
- Ensure SSL is properly configured

### **Email Sending Failures**

- Verify SendGrid API key
- Check sender email is verified in SendGrid
- Review SendGrid account limits

## 📝 **API Documentation**

Once running, visit:

- **Swagger UI**: `http://localhost:8000/api/docs`
- **ReDoc**: `http://localhost:8000/api/redoc`

## 🤝 **Contributing**

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 **License**

This project is licensed under the MIT License.

## 🆘 **Support**

For issues and questions:

1. Check the troubleshooting section
2. Review API documentation
3. Check Discord bot logs
4. Open an issue on GitHub

---

**Happy coding! 🚀**
