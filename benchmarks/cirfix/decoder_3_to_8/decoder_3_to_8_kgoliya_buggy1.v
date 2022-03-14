/******************************************************************
 * Date: Aug. 28, 1999
 * File: Decoder 3 to 8.v   (440 Examples)
 *
 * Module of a 3 to 8 Decoder with an active high enable input and
 * and active low outputs. This model uses a trinary continuous 
 * assignment statement for the combinational logic
 *******************************************************************/
//*****************************************************************
  module decoder_3to8(Y7, Y6, Y5, Y4, Y3, Y2, Y1, Y0, A, B, C, en);
//*****************************************************************
     output Y7, Y6, Y5, Y4, Y3, Y2, Y1, Y0;
     input  A, B, C;
     input  en;
     assign {Y7,Y6,Y5,Y4,Y3,Y2,Y1,Y0} <= ( {en,A,B,C} == 4'b1000) ? 8'b1111_1110 : // Hammad: This does not compile. Not usable for our experiments.
                                        ( {en,A,B,C} == 4'b1001) ? 8'b1111_1101 :
                                        ( {en,A,B,C} == 4'b1010) ? 8'b1111_1011 :
                                        ( {en,A,B,C} == 4'b1011) ? 8'b1111_0111 :
                                        ( {en,A,B,C} == 4'b1100) ? 8'b1110_1111 :
                                        ( {en,A,B,C} == 4'b1101) ? 8'b1101_1111 :
                                        ( {en,A,B,C} == 4'b1110) ? 8'b1011_1111 :
                                        ( {en,A,B,C} == 4'b1111) ? 8'b0111_1111 :
                                                                   8'b1111_1111;
  endmodule
