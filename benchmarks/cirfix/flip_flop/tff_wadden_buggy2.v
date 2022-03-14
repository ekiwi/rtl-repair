module tff (   input clk,
               input 	  rstn,
               input 	  t,
               output reg q);
   
   always @ (posedge clk) begin
    if (rstn) 
      q <= 0;
    else
      if (t)
        q <= q;
      else
        q <= ~q;
   end
endmodule
