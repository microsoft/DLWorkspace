using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;

namespace WindowsAuth
{
    public class UserItem
    {
        public string userId { get; set; }
        public string userName { get; set; }
        public bool isAuthed { get; set; }
        public string authenticationType { get; set; }
    }
}
