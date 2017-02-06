using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Mvc;

// For more information on enabling Web API for empty projects, visit http://go.microsoft.com/fwlink/?LinkID=397860

namespace WindowsAuth.Controllers
{
    [Route("api/user")]
    public class Users : Controller
    {
        // GET: api/values
        [HttpGet]
        public IActionResult Get()
        {
            UserItem useritem = new UserItem();
            useritem.userName = User.Identity.Name;
            useritem.isAuthed = User.Identity.IsAuthenticated;
            useritem.userId = User.Identity.Name;
            useritem.authenticationType = User.Identity.AuthenticationType;
            return new ObjectResult(useritem);
        }

        // GET api/values/5
        [HttpGet("{id}")]
        public string Get(int id)
        {
            return "value";
        }

    }
}
