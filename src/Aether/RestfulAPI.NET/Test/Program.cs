using System;
using DLWorkspaceUtils;
using System.Collections.Generic;

namespace Test
{
    class Program
    {
        static void Main(string[] args)
        {
            {
                Console.WriteLine(JobUtils.GetJobDetail("d17aa752-0683-4afd-83b3-32c4a55abb87"));
                return;
            }

            { 

                DLWorkspaceUtils.DataHandler dataHandler = new DLWorkspaceUtils.DataHandler();
                List<Job> jobs = dataHandler.GetJobList();
                foreach (var job in jobs)
                {
                    Console.WriteLine(job.ToString());
                }
                dataHandler.Close();
            }
        }
    }
}