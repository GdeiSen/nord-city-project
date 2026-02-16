#!/usr/bin/env python3
"""
Bot Service Main Entry Point
Handles microservices bot initialization and startup with comprehensive testing.

The bot service now also runs an internal HTTP server (FastAPI) to accept
RPC calls from other services (e.g. web_service requesting OTP code delivery).
"""

import asyncio
import logging
import os
import sys
import signal
import threading
from pathlib import Path
from typing import Optional, Dict, Any

# Load infrastructure .env first (single source of truth for ADMIN_CHAT_ID, BOT_TOKEN, etc.)
# So env is correct whether we're started by orchestrator or run standalone (e.g. python main.py)
_infra_root = Path(__file__).resolve().parents[3]
_env_path = _infra_root / ".env"
if _env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(_env_path, override=False)

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

# Add current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal HTTP RPC server for bot service
# ---------------------------------------------------------------------------

class BotRPCRequest(BaseModel):
    """Internal RPC request body."""
    service: str
    method: str
    params: Dict[str, Any] = {}


class BotRPCResponse(BaseModel):
    """Internal RPC response body."""
    success: bool
    data: Any = None
    error: Optional[str] = None


# Global reference to the bot instance and its event loop (set during startup)
_bot_instance = None
_main_loop: asyncio.AbstractEventLoop = None

bot_api = FastAPI(
    title="Nord City Bot Service (Internal)",
    description="Internal HTTP RPC endpoint for bot service operations.",
    version="1.0.0",
)


async def _execute_rpc(service_name: str, method_name: str, params: dict) -> BotRPCResponse:
    """Execute an RPC call within the bot's context (main event loop)."""
    bot = _bot_instance.agent.bot

    service = bot.services.get_service(service_name)
    method = getattr(service, method_name, None)

    if not method or not asyncio.iscoroutinefunction(method):
        return BotRPCResponse(
            success=False,
            error=f"Method '{method_name}' not found in service '{service_name}'."
        )

    result = await method(**params)

    if isinstance(result, dict) and "success" in result:
        return BotRPCResponse(**result)

    return BotRPCResponse(success=True, data=result)


@bot_api.post("/internal/rpc", response_model=BotRPCResponse)
async def bot_rpc_endpoint(request: BotRPCRequest):
    """
    Internal RPC endpoint for bot service.
    Allows other services to invoke bot service methods via HTTP.

    Since the HTTP server runs in a background thread, coroutines that
    depend on the bot (Telegram API, database client) must be scheduled
    on the main event loop where those objects were created.
    """
    global _bot_instance, _main_loop
    if _bot_instance is None or _bot_instance.agent is None or _bot_instance.agent.bot is None:
        return BotRPCResponse(success=False, error="Bot service is not ready")

    if _main_loop is None:
        return BotRPCResponse(success=False, error="Main event loop not available")

    try:
        # Schedule the coroutine on the main event loop and wait for result
        future = asyncio.run_coroutine_threadsafe(
            _execute_rpc(request.service, request.method, request.params),
            _main_loop,
        )
        # Block this thread until the main loop completes the call (with timeout)
        result = future.result(timeout=30)
        return result

    except AttributeError as e:
        logger.error(f"Service '{request.service}' not found: {e}")
        return BotRPCResponse(success=False, error=f"Service '{request.service}' not found.")
    except Exception as e:
        logger.error(f"RPC error in {request.service}.{request.method}: {e}", exc_info=True)
        return BotRPCResponse(success=False, error=f"Internal error: {str(e)}")


@bot_api.get("/health")
async def health_check():
    """Health check for the bot service HTTP endpoint."""
    global _bot_instance
    is_ready = (
        _bot_instance is not None
        and _bot_instance.agent is not None
        and _bot_instance.agent.bot is not None
    )
    return {
        "status": "healthy" if is_ready else "starting",
        "service": "bot_service",
        "bot_ready": is_ready,
    }


class BotServiceManager:
    """
    Main manager for bot service lifecycle in microservices architecture.
    
    This class handles the complete lifecycle of the Telegram bot service including:
    - Environment validation and configuration loading
    - Bot agent initialization with proper dependency injection
    - Service startup with error handling and graceful degradation
    - Signal handling for proper shutdown procedures
    
    The manager ensures all required environment variables are present,
    initializes the bot with microservices communication capabilities,
    and maintains service health throughout its lifecycle.
    
    Attributes:
        agent (Optional[Agent]): The main bot agent instance, None until initialized
        is_running (bool): Service running state flag for lifecycle management
    """
    
    def __init__(self):
        """
        Initialize the service manager with default state.
        
        Sets up initial state with no active agent and stopped status.
        The agent will be created during the initialization phase.
        """
        self.agent: Optional["Agent"] = None
        self.is_running = False
        
    async def run_startup_tests(self) -> bool:
        """
        Run comprehensive startup tests to verify service health.
        
        Note: This method is available for manual testing but is not 
        automatically called during service startup to prevent restart loops.
        
        Returns:
            bool: True if all tests pass, False otherwise
        """
        try:
            logger.info("Running startup tests...")
            
            # Import and run tests
            from test_service import run_startup_tests
            
            # Wait a bit for database service to be ready
            await asyncio.sleep(2)
            
            success = await run_startup_tests()
            
            if success:
                logger.info("✅ All startup tests passed - service is healthy")
            else:
                logger.error("❌ Startup tests failed - service has issues")
                
            return success
            
        except Exception as e:
            logger.error(f"Exception during startup tests: {e}")
            return False
    
    async def initialize_bot(self) -> bool:
        """
        Initialize the bot agent with microservices configuration from environment.
        
        This method performs critical environment validation and bot agent creation:
        - Validates required environment variables (BOT_TOKEN, ADMIN_CHAT_ID)
        - Extracts database connection parameters
        - Creates and configures the main Agent instance
        - Prepares the bot for microservices communication
        
        Environment Variables Required:
            BOT_TOKEN (str): Telegram Bot API token for authentication
            ADMIN_CHAT_ID (str): Primary administrator chat ID for notifications
            CHIEF_ENGINEER_CHAT_ID (str, optional): Secondary admin chat ID
            DATABASE_URL (str, optional): PostgreSQL connection string, defaults to Docker setup
        
        Returns:
            bool: True if bot initialization successful, False if validation fails
            
        Raises:
            Exception: Logged and handled gracefully, returns False on any error
        """
        try:
            logger.info("Initializing bot service...")
            
            # Get configuration from environment
            token = os.getenv('BOT_TOKEN')
            database_url = os.getenv('DATABASE_URL', 'postgresql://bot_user:bot_password@postgres:5432/bot_database')
            admin_chat_id = os.getenv('ADMIN_CHAT_ID')
            chief_engineer_chat_id = os.getenv('CHIEF_ENGINEER_CHAT_ID')
            
            if not token:
                logger.error("BOT_TOKEN environment variable is required")
                return False
                
            if not admin_chat_id:
                logger.error("ADMIN_CHAT_ID environment variable is required")
                return False
            
            # Import and initialize agent
            from bot import Agent
            
            self.agent = Agent()
            
            logger.info("Bot service initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize bot: {e}")
            return False
    
    async def start_bot(self) -> bool:
        """
        Start the bot service.
        
        Returns:
            bool: True if startup successful
        """
        try:
            if not self.agent:
                logger.error("Bot agent not initialized")
                return False
            
            logger.info("Starting bot service...")
            
            # Get configuration from environment
            token = os.getenv('BOT_TOKEN')
            database_url = os.getenv('DATABASE_URL', 'postgresql://bot_user:bot_password@postgres:5432/bot_database')
            admin_chat_id = os.getenv('ADMIN_CHAT_ID')
            chief_engineer_chat_id = os.getenv('CHIEF_ENGINEER_CHAT_ID')
            
            # Start the bot
            await self.agent.start_async(token, database_url, admin_chat_id, chief_engineer_chat_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
            return False
    
    def _start_http_server(self):
        """Start the internal HTTP RPC server in a background thread."""
        host = os.getenv("BOT_SERVICE_HOST", "0.0.0.0")
        port = int(os.getenv("BOT_SERVICE_PORT", "8002"))
        logger.info(f"Starting Bot Service HTTP server on {host}:{port}")

        config = uvicorn.Config(
            bot_api,
            host=host,
            port=port,
            log_level="warning",
        )
        server = uvicorn.Server(config)

        def _run():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(server.serve())

        thread = threading.Thread(target=_run, daemon=True, name="bot-http-server")
        thread.start()
        logger.info(f"Bot Service HTTP server started on {host}:{port}")

    async def run(self):
        """
        Run the complete bot service lifecycle.
        
        Includes:
        1. Bot initialization  
        2. Internal HTTP RPC server startup
        3. Bot startup
        4. Graceful shutdown handling
        
        Note: Startup tests can be run manually using test_service.py
        """
        global _bot_instance, _main_loop
        _bot_instance = self
        _main_loop = asyncio.get_event_loop()

        try:
            logger.info("🚀 Starting Bot Service...")
            
            # Step 1: Initialize bot
            if not await self.initialize_bot():
                logger.error("Bot initialization failed - aborting service start")
                sys.exit(1)
            
            # Step 2: Start internal HTTP server (runs in background thread)
            self._start_http_server()

            # Step 3: Start bot
            if not await self.start_bot():
                logger.error("Bot startup failed - aborting service start")
                sys.exit(1)
            
            logger.info("✅ Bot service started successfully")
            self.is_running = True
            
            # Keep running until interrupted
            while self.is_running:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except Exception as e:
            logger.error(f"Unexpected error in service: {e}")
            sys.exit(1)
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Graceful shutdown of the service"""
        logger.info("Shutting down bot service...")
        self.is_running = False
        
        if self.agent and hasattr(self.agent, 'bot') and self.agent.bot:
            try:
                if hasattr(self.agent.bot, 'application') and self.agent.bot.application:
                    await self.agent.bot.application.stop()
                    await self.agent.bot.application.shutdown()
                logger.info("Bot service shutdown completed")
            except Exception as e:
                logger.error(f"Error during shutdown: {e}")


def setup_signal_handlers(service_manager: BotServiceManager):
    """Set up signal handlers for graceful shutdown"""
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}")
        service_manager.is_running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


async def main():
    """Main entry point for the bot service"""
    logger.info("Initializing bot service...")
    
    service_manager = BotServiceManager()
    setup_signal_handlers(service_manager)
    
    try:
        await service_manager.run()
    except Exception as e:
        logger.error(f"Fatal error in main: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 