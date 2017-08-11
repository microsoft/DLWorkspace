using System.Collections.Concurrent;
using System;

namespace WindowsAuth.models
{
    public interface IFamily { }
    
    public class FamilyModel : IFamily
    {
	public struct FamilyData
	{
	    public string ApiPath;
	    public string Email;
	    public string UID;
	}
	public ConcurrentDictionary<Guid, FamilyData> Families { get; set; }

	public FamilyModel() {
	    Families = new ConcurrentDictionary<Guid, FamilyData>();
	}
    }
}
