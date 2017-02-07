using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Mvc;
using WindowsAuth.models;

// For more information on enabling Web API for empty projects, visit http://go.microsoft.com/fwlink/?LinkID=397860

namespace WindowsAuth.Controllers
{
    [Route("api/[controller]")]
    public class UsersController : Controller
    {
        // GET: api/users
        [HttpGet]
        public IActionResult Get()
        {
            UserID useritem = new UserID();
            useritem.userName = User.Identity.Name;
            useritem.isAuthed = User.Identity.IsAuthenticated;
            useritem.userId = User.Identity.Name;
            useritem.authenticationType = User.Identity.AuthenticationType;
            return new ObjectResult(useritem);
        }
    }
}
